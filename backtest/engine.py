from dataclasses import dataclass
from typing import Dict

import pandas as pd

from risk.position_sizer import PositionSizer
from risk.risk_manager import RiskManager

from strategy.indicators import IndicatorEngine
from strategy.signal_engine import SignalEngine, Signal

from data.fundamental_context import FundamentalContextEngine
from strategy.alpha_engine import CombinedAlphaEngine

from regime.market_regime import MarketRegimeEngine

from backtest.portfolio import Portfolio
from backtest.metrics import PerformanceMetrics


@dataclass
class BacktestConfig:
    initial_capital: float = 200.0


class BacktestEngine:

    def __init__(
        self,
        settings,
        config: BacktestConfig | None = None,
    ):
        self.settings = settings
        self.config = config if config is not None else BacktestConfig()

        self.indicator_engine = IndicatorEngine(settings)
        self.signal_engine = SignalEngine(settings)
        self.market_regime_engine = MarketRegimeEngine(settings)
        self.fundamental_context_engine = FundamentalContextEngine(settings)
        self.combined_alpha_engine = CombinedAlphaEngine()
        self.position_sizer = PositionSizer(settings)
        self.risk_manager = RiskManager(trading_client=None, settings=settings)

        self._reset_runtime_state()

    def _reset_runtime_state(self):
        self.portfolio = Portfolio(
            initial_capital=self.config.initial_capital,
            cash=self.config.initial_capital,
        )
        self.risk_manager = RiskManager(
            trading_client=None,
            settings=self.settings,
        )
        self.cooldowns = {}
        self.daily_start_equity = self.config.initial_capital
        self.current_day = None
        self.daily_trading_done = False
        self.daily_tp1_hit = False
        self.daily_loss_limit_hit = False

        self.ambiguous_bar_count = 0
        self.stop_hit_count = 0
        self.target_hit_count = 0
        self.daily_tp1_hit_count = 0
        self.daily_tp2_hit_count = 0
        self.daily_loss_limit_hit_count = 0
        self.trade_attempt_count = 0

        self.fundamental_context_count = 0
        self.fundamental_unavailable_count = 0
        self.fundamental_rejected_count = 0
        self.multi_factor_trade_count = 0
        self.technical_fallback_trade_count = 0

    def prepare_data(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        if df.empty:
            raise ValueError("Backtest verisi boş.")
        if not isinstance(df.index, pd.MultiIndex):
            raise ValueError("Backtest DataFrame MultiIndex kullanmalıdır.")
        if "symbol" not in df.index.names:
            raise ValueError("DataFrame index içinde 'symbol' bulunamadı.")

        prepared = {}
        available_symbols = set(df.index.get_level_values("symbol"))

        for symbol in self.settings.universe:
            if symbol not in available_symbols:
                continue
            symbol_df = df.xs(symbol, level="symbol").copy().sort_index()
            symbol_df = self.indicator_engine.calculate(symbol_df)
            prepared[symbol] = symbol_df

        if not prepared:
            raise ValueError("Universe içerisinde kullanılabilir sembol bulunamadı.")

        return prepared

    def build_timeline(self, prepared_data, start_date=None, end_date=None):
        timestamps = set()
        for symbol_df in prepared_data.values():
            timestamps.update(symbol_df.index)

        sorted_ts = sorted(timestamps)
        if not sorted_ts:
            return []

        sample_tz = sorted_ts[0].tzinfo

        if start_date is not None:
            start = pd.Timestamp(start_date)
            if sample_tz is not None:
                start = start.tz_localize(sample_tz) if start.tzinfo is None else start.tz_convert(sample_tz)
            sorted_ts = [ts for ts in sorted_ts if ts >= start]

        if end_date is not None:
            end = pd.Timestamp(end_date)
            if sample_tz is not None:
                end = end.tz_localize(sample_tz) if end.tzinfo is None else end.tz_convert(sample_tz)
            sorted_ts = [ts for ts in sorted_ts if ts <= end]

        return sorted_ts

    def get_current_equity(self, prices=None) -> float:
        if prices is None:
            prices = {}
        return self.portfolio.calculate_equity(prices)

    def reset_daily_state(self, timestamp, prices):
        current_day = timestamp.date()
        if self.current_day == current_day:
            return
        self.current_day = current_day
        self.daily_start_equity = self.get_current_equity(prices)
        self.daily_trading_done = False
        self.daily_tp1_hit = False
        self.daily_loss_limit_hit = False

    def calculate_daily_return(self, equity: float) -> float:
        if self.daily_start_equity <= 0:
            return 0.0
        return (equity / self.daily_start_equity) - 1.0

    def check_daily_loss_limit(self, equity: float) -> bool:
        daily_return = self.calculate_daily_return(equity)
        if daily_return <= self.settings.max_daily_loss_pct * -1:
            if not self.daily_loss_limit_hit:
                self.daily_loss_limit_hit = True
                self.daily_loss_limit_hit_count += 1
            return True
        return False

    def is_in_cooldown(self, symbol, timestamp) -> bool:
        last_exit = self.cooldowns.get(symbol)
        if last_exit is None:
            return False
        elapsed = timestamp - last_exit
        elapsed_minutes = elapsed.total_seconds() / 60.0
        required_minutes = (
            self.settings.cooldown_bars * self.settings.timeframe_minutes
        )
        return elapsed_minutes < required_minutes

    def register_position_risk(self, symbol, quantity, entry_price, stop_price):
        self.risk_manager.register_position_risk(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_price=stop_price,
        )

    def unregister_position_risk(self, symbol):
        self.risk_manager.unregister_position(symbol)

    @staticmethod
    def _get_factor_value(factor, name, default=None):
        if factor is None:
            return default
        return getattr(factor, name, default)

    def build_ranked_candidates(self, timestamp, next_timestamp, prepared_data):
        candidates = []

        market_regime = None
        market_regime_result = None
        spy_above_ema50 = True

        benchmark_df = prepared_data.get("SPY")
        if benchmark_df is not None and timestamp in benchmark_df.index:
            benchmark_history = benchmark_df.loc[:timestamp]
            if len(benchmark_history) >= 30:
                market_regime_result = self.market_regime_engine.evaluate(
                    benchmark_history
                )
                market_regime = market_regime_result.regime
                # SPY 50 günlük ortalamasının altındaysa (2022 Ayı Piyasası filtresi)
                if "price_vs_ema50" in benchmark_history.columns:
                    spy_vs_50 = benchmark_history.iloc[-1]["price_vs_ema50"]
                    if pd.notna(spy_vs_50) and float(spy_vs_50) < 0:
                        spy_above_ema50 = False

        non_tradable = set(
            getattr(self.settings, "non_tradable_symbols", ("SPY", "TSLA"))
        )

        regime_str = str(getattr(market_regime, "value", market_regime or "")).upper()

        for symbol, symbol_df in prepared_data.items():
            if symbol.upper() in non_tradable:
                continue
            if timestamp not in symbol_df.index or next_timestamp not in symbol_df.index:
                continue

            history = symbol_df.loc[:timestamp]
            if len(history) < 52:
                continue

            signal_result = self.signal_engine.evaluate(
                symbol=symbol,
                df=history,
                market_regime=market_regime,
            )

            if signal_result.signal != Signal.BUY:
                continue

            try:
                fundamental_context = self.fundamental_context_engine.get_context(
                    symbol=symbol,
                    as_of_date=timestamp.date(),
                )
                self.fundamental_context_count += 1
            except Exception:
                fundamental_context = None
                self.fundamental_unavailable_count += 1

            fundamental_factor = (
                fundamental_context.factor if fundamental_context is not None else None
            )
            fundamental_score = (
                fundamental_factor.fundamental_score if fundamental_factor is not None else None
            )
            data_quality_score = (
                fundamental_factor.data_quality_score if fundamental_factor is not None else None
            )

            alpha_result = self.combined_alpha_engine.calculate(
                symbol=symbol,
                technical_score=signal_result.score,
                fundamental_score=fundamental_score,
                regime=market_regime or "UNKNOWN",
                data_quality_score=data_quality_score,
            )

            if not alpha_result.eligible:
                self.fundamental_rejected_count += 1
                continue

            # ====================================================
            # 2022 BEAR / SIDEWAYS & QUALITY FILTER
            # ====================================================
            # 1. SPY 50 EMA altındaysa veya rejim SIDEWAYS ise sadece ultra-elit sinyallere gir!
            if "SIDEWAYS" in regime_str or not spy_above_ema50:
                if alpha_result.final_score < 82.0 or signal_result.score < 78:
                    continue

            # 2. Bilanço verisi yoksa (Technical Fallback), teknik skor en az 74 olmalı!
            if fundamental_score is None and signal_result.score < 74:
                continue

            candidates.append({
                "symbol": symbol,
                "signal": signal_result,
                "history": history,
                "next_bar": symbol_df.loc[next_timestamp],
                "market_regime": market_regime_result,
                "fundamental_context": fundamental_context,
                "fundamental_factor": fundamental_factor,
                "alpha_result": alpha_result,
            })

        candidates.sort(
            key=lambda c: (
                c["alpha_result"].final_score,
                c["alpha_result"].technical_score,
                c["symbol"],
            ),
            reverse=True,
        )

        return candidates

    def try_open_position(
        self,
        symbol,
        timestamp,
        history,
        next_bar,
        prices,
        signal_result=None,
        alpha_result=None,
    ) -> bool:

        self.trade_attempt_count += 1

        non_tradable = set(
            getattr(self.settings, "non_tradable_symbols", ("SPY", "TSLA"))
        )
        if symbol.upper() in non_tradable:
            return False

        if (
            self.daily_trading_done
            or self.daily_tp1_hit
            or self.daily_loss_limit_hit
        ):
            return False

        if symbol in self.portfolio.positions:
            return False

        equity = self.get_current_equity(prices)
        if equity <= 0:
            return False

        if self.check_daily_loss_limit(equity):
            return False

        if self.is_in_cooldown(symbol, timestamp):
            return False

        signal = signal_result
        if signal is None:
            signal = self.signal_engine.evaluate(symbol=symbol, df=history)

        if signal.signal != Signal.BUY:
            return False

        if alpha_result is None:
            fundamental_context = None
            fundamental_factor = None
            fundamental_score = None
            data_quality_score = None

            try:
                fundamental_context = self.fundamental_context_engine.get_context(
                    symbol=symbol,
                    as_of_date=timestamp.date(),
                )
                self.fundamental_context_count += 1
                fundamental_factor = fundamental_context.factor
                if fundamental_factor is not None:
                    fundamental_score = fundamental_factor.fundamental_score
                    data_quality_score = fundamental_factor.data_quality_score
            except Exception:
                self.fundamental_unavailable_count += 1

            signal_regime = getattr(signal, "regime", "UNKNOWN")
            alpha_result = self.combined_alpha_engine.calculate(
                symbol=symbol,
                technical_score=signal.score,
                fundamental_score=fundamental_score,
                regime=signal_regime or "UNKNOWN",
                data_quality_score=data_quality_score,
            )

        if not alpha_result.eligible:
            return False

        entry_price = float(next_bar["open"])
        if entry_price <= 0:
            return False

        atr_value = history.iloc[-1]["atr"]
        if pd.isna(atr_value):
            return False
        atr = float(atr_value)
        if atr <= 0:
            return False

        # ====================================================
        # 2.5X BUYING POWER DESTEKLİ POSITION SIZING
        # ====================================================
        available_bp = (
            self.portfolio.get_buying_power(prices)
            if hasattr(self.portfolio, "get_buying_power")
            else self.portfolio.cash
        )

        try:
            position_size = self.position_sizer.calculate(
                symbol=symbol,
                entry_price=entry_price,
                atr=atr,
                equity=equity,
                available_cash=available_bp,
            )
        except ValueError:
            return False

        quantity = position_size.quantity
        stop_price = position_size.stop_price
        target_price = position_size.target_price

        use_fixed_target = bool(getattr(self.settings, "use_fixed_target", False))
        if not use_fixed_target:
            target_price = None

        if quantity <= 0:
            return False

        risk_decision = self.risk_manager.approve_position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_price=stop_price,
            equity=equity,
            daily_pnl_pct=self.calculate_daily_return(equity),
        )

        if not risk_decision.approved:
            return False

        alpha_mode = (
            getattr(alpha_result, "alpha_mode", None)
            or (
                "MULTI_FACTOR"
                if alpha_result.fundamental_score is not None
                else "TECHNICAL_FALLBACK"
            )
        )

        fundamental_available = getattr(alpha_result, "fundamental_available", None)
        if fundamental_available is None:
            fundamental_available = alpha_result.fundamental_score is not None

        fundamental_factor = None
        if fundamental_available and alpha_result.fundamental_score is not None:
            try:
                context = self.fundamental_context_engine.get_context(
                    symbol=symbol,
                    as_of_date=history.index[-1].date(),
                )
                fundamental_factor = context.factor
            except Exception:
                fundamental_factor = None

        position_value = float(position_size.position_value)
        exposure_pct = (position_value / equity) if equity > 0 else 0.0

        last_bar = history.iloc[-1]

        entry_metrics = {
            "rsi": float(last_bar["rsi"]) if ("rsi" in last_bar and pd.notna(last_bar["rsi"])) else 0.0,
            "volume_ratio": float(last_bar["volume_ratio"]) if ("volume_ratio" in last_bar and pd.notna(last_bar["volume_ratio"])) else 0.0,
            "macd": float(last_bar["macd"]) if ("macd" in last_bar and pd.notna(last_bar["macd"])) else 0.0,
            "macd_histogram": float(last_bar["macd_histogram"]) if ("macd_histogram" in last_bar and pd.notna(last_bar["macd_histogram"])) else 0.0,
            "price_vs_ema50": float(last_bar["price_vs_ema50"]) if ("price_vs_ema50" in last_bar and pd.notna(last_bar["price_vs_ema50"])) else 0.0,
            "volume_breakout": bool(last_bar["volume_breakout"]) if ("volume_breakout" in last_bar and pd.notna(last_bar["volume_breakout"])) else False,
            "atr": atr,
            "stop_distance": position_size.stop_distance,
            "target_distance": position_size.target_distance,
            "risk_reward_ratio": position_size.risk_reward_ratio,
            "position_value": position_size.position_value,
            "risk_amount": position_size.risk_amount,
            "entry_equity": equity,
            "exposure_pct": exposure_pct * 100.0,
            "max_total_open_risk": risk_decision.max_total_open_risk,
            "projected_open_risk": risk_decision.projected_open_risk,
            "signal_score": signal.score,
            "technical_score": alpha_result.technical_score,
            "fundamental_score": alpha_result.fundamental_score,
            "alpha_score": alpha_result.final_score,
            "alpha_base_score": alpha_result.base_score,
            "alpha_regime_adjustment": alpha_result.regime_adjustment,
            "fundamental_data_quality": alpha_result.data_quality_score,
            "fundamental_available": fundamental_available,
            "alpha_mode": alpha_mode,
            "alpha_reason": alpha_result.reason,
            "market_regime": alpha_result.regime,
            "revenue_growth": self._get_factor_value(fundamental_factor, "revenue_growth"),
            "net_income_growth": self._get_factor_value(fundamental_factor, "net_income_growth"),
            "eps_growth": self._get_factor_value(fundamental_factor, "eps_growth"),
            "revenue_ttm_growth": self._get_factor_value(fundamental_factor, "revenue_ttm_growth"),
            "net_income_ttm_growth": self._get_factor_value(fundamental_factor, "net_income_ttm_growth"),
            "eps_ttm_growth": self._get_factor_value(fundamental_factor, "eps_ttm_growth"),
            "fcf_ttm_growth": self._get_factor_value(fundamental_factor, "fcf_ttm_growth"),
            "net_margin": self._get_factor_value(fundamental_factor, "net_margin"),
            "roe": self._get_factor_value(fundamental_factor, "roe"),
            "free_cash_flow_margin": self._get_factor_value(fundamental_factor, "free_cash_flow_margin"),
            "earnings_quality": self._get_factor_value(fundamental_factor, "earnings_quality"),
            "debt_to_assets": self._get_factor_value(fundamental_factor, "debt_to_assets"),
            "cash_to_assets": self._get_factor_value(fundamental_factor, "cash_to_assets"),
        }

        if alpha_mode == "MULTI_FACTOR":
            self.multi_factor_trade_count += 1
        elif alpha_mode == "TECHNICAL_FALLBACK":
            self.technical_fallback_trade_count += 1

        try:
            self.portfolio.open_position(
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                entry_time=timestamp,
                entry_signal_score=signal.score,
                entry_metrics=entry_metrics,
            )
        except ValueError:
            return False

        self.register_position_risk(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_price=stop_price,
        )

        return True

    def manage_position(self, symbol, timestamp, bar) -> bool:
        if symbol not in self.portfolio.positions:
            return False

        position = self.portfolio.positions[symbol]

        try:
            high = float(bar["high"])
            low = float(bar["low"])
            close = float(bar["close"])
        except (KeyError, TypeError, ValueError):
            return False

        if high <= 0 or low <= 0 or close <= 0:
            return False

        initial_risk = position.entry_price - position.initial_stop_price
        if initial_risk <= 0:
            return False

        current_stop = float(position.stop_price)
        stop_hit = (low <= current_stop)

        use_fixed_target = bool(getattr(self.settings, "use_fixed_target", False))
        target_hit = False
        if use_fixed_target and position.target_price is not None:
            target_hit = (high >= float(position.target_price))

        if stop_hit and target_hit:
            self.ambiguous_bar_count += 1
            self.portfolio.close_position(
                symbol=symbol,
                exit_price=current_stop,
                exit_time=timestamp,
                exit_reason="STOP_AMBIGUOUS_BAR",
            )
            self.unregister_position_risk(symbol)
            self.stop_hit_count += 1
            self.cooldowns[symbol] = timestamp
            return True

        if stop_hit:
            self.portfolio.close_position(
                symbol=symbol,
                exit_price=current_stop,
                exit_time=timestamp,
                exit_reason="STOP",
            )
            self.unregister_position_risk(symbol)
            self.stop_hit_count += 1
            self.cooldowns[symbol] = timestamp
            return True

        if target_hit:
            self.portfolio.close_position(
                symbol=symbol,
                exit_price=position.target_price,
                exit_time=timestamp,
                exit_reason="TARGET",
            )
            self.unregister_position_risk(symbol)
            self.target_hit_count += 1
            self.cooldowns[symbol] = timestamp
            return True

        self.portfolio.update_position_state(symbol=symbol, current_price=close)
        position = self.portfolio.positions[symbol]

        if high > position.highest_price:
            position.highest_price = high

        position.current_r = (close - position.entry_price) / initial_risk
        high_r = (high - position.entry_price) / initial_risk
        peak_r = (position.highest_price - position.entry_price) / initial_risk

        # ====================================================
        # TIME-STOP (7 GÜNDE HİÇ +0.40R GÖREMEMİŞ ÖLÜ İŞLEMLER)
        # ====================================================
        time_stop_bars = int(getattr(self.settings, "time_stop_bars", 7))
        try:
            days_held = (timestamp - position.entry_time).total_seconds() / 86400.0
        except Exception:
            days_held = 0.0

        if days_held >= time_stop_bars and peak_r < 0.40 and position.current_r < -0.15:
            self.portfolio.close_position(
                symbol=symbol,
                exit_price=close,
                exit_time=timestamp,
                exit_reason="STOP",
            )
            self.unregister_position_risk(symbol)
            self.stop_hit_count += 1
            self.cooldowns[symbol] = timestamp
            return True

        atr = None
        if "atr" in bar:
            try:
                atr = float(bar["atr"])
            except (TypeError, ValueError):
                atr = None

        bar_rsi = None
        if "rsi" in bar and pd.notna(bar["rsi"]):
            try:
                bar_rsi = float(bar["rsi"])
            except (TypeError, ValueError):
                bar_rsi = None

        new_stop = position.stop_price
        management_reason = None

        # ====================================================
        # 1. BREAK EVEN PLUS (+0.75R'DE +0.20R GARANTİ KÂR)
        # ====================================================
        break_even_at_r = float(getattr(self.settings, "break_even_at_r", 0.75))
        break_even_offset_r = float(getattr(self.settings, "break_even_offset_r", 0.20))
        be_stop = position.entry_price + (initial_risk * break_even_offset_r)

        if high_r >= break_even_at_r and position.stop_price < be_stop:
            new_stop = max(new_stop, be_stop)
            management_reason = "BREAK_EVEN_PLUS"

        # ====================================================
        # 2. PROFIT LOCK (+1.30R'DE +0.70R KÂR KİLİDİ)
        # ====================================================
        lock_profit_at_r = float(getattr(self.settings, "lock_profit_at_r", 1.30))
        lock_profit_r = float(getattr(self.settings, "lock_profit_r", 0.70))
        lock_stop = position.entry_price + (initial_risk * lock_profit_r)

        if high_r >= lock_profit_at_r and position.stop_price < lock_stop:
            new_stop = max(new_stop, lock_stop)
            management_reason = "PROFIT_LOCK"

        # ====================================================
        # 3. ATR TRAILING & PARABOLIC LOCK ($415+ PNL ENGINE)
        # ====================================================
        trailing_start_at_r = float(getattr(self.settings, "trailing_start_at_r", 1.70))
        trailing_atr_multiplier = float(getattr(self.settings, "trailing_atr_multiplier", 1.45))

        parabolic_rsi_threshold = float(getattr(self.settings, "parabolic_rsi_threshold", 77.0))
        parabolic_atr_multiplier = float(getattr(self.settings, "parabolic_atr_multiplier", 0.85))

        is_parabolic_blowoff = (
            (high_r >= 2.2 and bar_rsi is not None and bar_rsi >= parabolic_rsi_threshold)
            or high_r >= 3.5
        )

        active_atr_mult = (
            parabolic_atr_multiplier if is_parabolic_blowoff else trailing_atr_multiplier
        )

        if high_r >= trailing_start_at_r and atr is not None and atr > 0:
            trailing_stop = position.highest_price - (atr * active_atr_mult)
            if trailing_stop > new_stop:
                new_stop = trailing_stop
                management_reason = (
                    "PARABOLIC_TRAILING" if is_parabolic_blowoff else "ATR_TRAILING"
                )

        if new_stop > position.stop_price:
            updated = self.portfolio.update_stop_price(
                symbol=symbol,
                new_stop_price=new_stop,
            )

            if updated:
                current_position = self.portfolio.positions[symbol]
                self.unregister_position_risk(symbol)

                # Stop maliyetin üstüne çıktığında artık risk 0'dır (Free-Roll).
                # RiskManager'dan düşerek yeni işlemlere yer açar!
                if current_position.stop_price < current_position.entry_price:
                    self.register_position_risk(
                        symbol=symbol,
                        quantity=current_position.quantity,
                        entry_price=current_position.entry_price,
                        stop_price=current_position.stop_price,
                    )

                current_position.entry_metrics["last_stop_management"] = management_reason
                current_position.entry_metrics["last_stop_update_r"] = current_position.stop_r

        return False

    def run(self, df: pd.DataFrame, start_date=None, end_date=None):
        self._reset_runtime_state()
        prepared = self.prepare_data(df)

        if not prepared:
            raise ValueError("Belirtilen tarih aralığında backtest verisi bulunamadı.")

        timeline = self.build_timeline(
            prepared, start_date=start_date, end_date=end_date
        )
        if len(timeline) < 3:
            raise ValueError("Backtest için yeterli veri bulunmuyor.")

        print(f"[BACKTEST] {len(timeline)} zaman noktası işlenecek.")

        for i in range(1, len(timeline) - 1):
            timestamp = timeline[i]
            next_timestamp = timeline[i + 1]

            current_prices = {}
            for symbol, symbol_df in prepared.items():
                if timestamp not in symbol_df.index:
                    continue
                current_prices[symbol] = float(symbol_df.loc[timestamp]["close"])

            self.reset_daily_state(timestamp=timestamp, prices=current_prices)

            for symbol, symbol_df in prepared.items():
                if timestamp not in symbol_df.index:
                    continue
                self.manage_position(
                    symbol=symbol,
                    timestamp=timestamp,
                    bar=symbol_df.loc[timestamp],
                )

            current_equity = self.get_current_equity(current_prices)
            daily_return = self.calculate_daily_return(current_equity)

            self.check_daily_loss_limit(current_equity)

            if (
                getattr(self.settings, "daily_tp2_enabled", True)
                and daily_return >= self.settings.daily_tp2_pct
                and not self.daily_trading_done
            ):
                for symbol in list(self.portfolio.positions.keys()):
                    if symbol not in current_prices:
                        continue
                    self.portfolio.close_position(
                        symbol=symbol,
                        exit_price=current_prices[symbol],
                        exit_time=timestamp,
                        exit_reason="DAILY_TP2",
                    )
                    self.unregister_position_risk(symbol)
                    self.cooldowns[symbol] = timestamp

                self.daily_trading_done = True
                self.daily_tp2_hit_count += 1

            elif (
                getattr(self.settings, "daily_tp1_enabled", True)
                and daily_return >= self.settings.daily_tp1_pct
                and not self.daily_tp1_hit
            ):
                self.daily_tp1_hit = True
                self.daily_tp1_hit_count += 1

            if not (
                self.daily_trading_done
                or self.daily_tp1_hit
                or self.daily_loss_limit_hit
            ):
                ranked_candidates = self.build_ranked_candidates(
                    timestamp=timestamp,
                    next_timestamp=next_timestamp,
                    prepared_data=prepared,
                )

                for candidate in ranked_candidates:
                    if (
                        self.daily_trading_done
                        or self.daily_tp1_hit
                        or self.daily_loss_limit_hit
                    ):
                        break

                    max_open_positions = int(
                        getattr(self.settings, "max_open_positions", 3)
                    )
                    if len(self.portfolio.positions) >= (max_open_positions + 1):
                        break

                    self.try_open_position(
                        symbol=candidate["symbol"],
                        timestamp=next_timestamp,
                        history=candidate["history"],
                        next_bar=candidate["next_bar"],
                        prices=current_prices,
                        signal_result=candidate["signal"],
                        alpha_result=candidate["alpha_result"],
                    )

            self.portfolio.record_equity(
                timestamp=timestamp,
                prices=current_prices,
                daily_start_equity=self.daily_start_equity,
                daily_return_pct=daily_return * 100.0,
                daily_loss_limit_hit=self.daily_loss_limit_hit,
                daily_tp1_hit=self.daily_tp1_hit,
                daily_tp2_hit=self.daily_trading_done,
            )

        final_timestamp = timeline[-1]
        final_prices = {}

        for symbol, symbol_df in prepared.items():
            if final_timestamp not in symbol_df.index:
                continue
            final_prices[symbol] = float(symbol_df.loc[final_timestamp, "close"])

        for symbol in list(self.portfolio.positions.keys()):
            if symbol not in final_prices:
                continue
            self.portfolio.close_position(
                symbol=symbol,
                exit_price=final_prices[symbol],
                exit_time=final_timestamp,
                exit_reason="END_OF_BACKTEST",
            )
            self.unregister_position_risk(symbol)

        final_equity = self.get_current_equity(final_prices)
        final_daily_return = self.calculate_daily_return(final_equity)

        self.portfolio.record_equity(
            timestamp=final_timestamp,
            prices=final_prices,
            daily_start_equity=self.daily_start_equity,
            daily_return_pct=final_daily_return * 100.0,
            daily_loss_limit_hit=self.daily_loss_limit_hit,
            daily_tp1_hit=self.daily_tp1_hit,
            daily_tp2_hit=self.daily_trading_done,
        )

        metrics = PerformanceMetrics(self.portfolio)
        result = metrics.calculate()

        result.update({
            "ambiguous_bars": self.ambiguous_bar_count,
            "stop_hits": self.stop_hit_count,
            "target_hits": self.target_hit_count,
            "daily_tp1_days": self.daily_tp1_hit_count,
            "daily_tp2_days": self.daily_tp2_hit_count,
            "daily_loss_limit_days": self.daily_loss_limit_hit_count,
            "trade_attempts": self.trade_attempt_count,
            "fundamental_contexts": self.fundamental_context_count,
            "fundamental_unavailable": self.fundamental_unavailable_count,
            "fundamental_rejected": self.fundamental_rejected_count,
            "multi_factor_trades": self.multi_factor_trade_count,
            "technical_fallback_trades": self.technical_fallback_trade_count,
            "final_open_risk": self.risk_manager.calculate_total_open_risk(),
        })

        return result