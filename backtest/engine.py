from dataclasses import dataclass
from typing import Dict

import pandas as pd

from risk.position_sizer import PositionSizer
from risk.risk_manager import RiskManager

from strategy.indicators import IndicatorEngine
from strategy.signal_engine import SignalEngine, Signal

from data.fundamental_context import FundamentalContextEngine
from strategy.alpha_engine import CombinedAlphaEngine

from regime.market_regime import (
    MarketRegimeEngine,
)

from backtest.portfolio import Portfolio
from backtest.metrics import PerformanceMetrics


# ============================================================
# BACKTEST CONFIGURATION
# ============================================================

@dataclass
class BacktestConfig:
    """
    Sadece backtest'e özel ayarlar.

    Risk / trading parametrelerinin kaynağı
    config.settings.Settings'tir.
    """

    initial_capital: float = 200.0


# ============================================================
# BACKTEST ENGINE V3.0 (HIGH-VELOCITY COMPOUNDING REVISION)
# ============================================================

class BacktestEngine:

    def __init__(
        self,
        settings,
        config: BacktestConfig | None = None,
    ):

        self.settings = settings

        self.config = (
            config
            if config is not None
            else BacktestConfig()
        )

        # ----------------------------------------------------
        # COMPONENTS
        # ----------------------------------------------------

        self.indicator_engine = (
            IndicatorEngine(settings)
        )

        self.signal_engine = (
            SignalEngine(settings)
        )

        self.market_regime_engine = (
            MarketRegimeEngine(settings)
        )

        self.fundamental_context_engine = (
            FundamentalContextEngine(settings)
        )

        self.combined_alpha_engine = (
            CombinedAlphaEngine()
        )

        self.position_sizer = (
            PositionSizer(settings)
        )

        self.risk_manager = (
            RiskManager(
                trading_client=None,
                settings=settings,
            )
        )

        # ----------------------------------------------------
        # RUNTIME STATE
        # ----------------------------------------------------

        self._reset_runtime_state()

    # ========================================================
    # RESET RUNTIME STATE
    # ========================================================

    def _reset_runtime_state(self):
        """
        Her backtest run'ı tamamen temiz bir state ile başlatır.
        """

        self.portfolio = Portfolio(
            initial_capital=(
                self.config.initial_capital
            ),
            cash=(
                self.config.initial_capital
            ),
        )

        self.risk_manager = (
            RiskManager(
                trading_client=None,
                settings=self.settings,
            )
        )

        self.cooldowns = {}

        self.daily_start_equity = (
            self.config.initial_capital
        )

        self.current_day = None

        self.daily_trading_done = False

        self.daily_tp1_hit = False

        self.daily_loss_limit_hit = False

        # ----------------------------------------------------
        # ANALYTICS
        # ----------------------------------------------------

        self.ambiguous_bar_count = 0

        self.stop_hit_count = 0

        self.target_hit_count = 0

        self.daily_tp1_hit_count = 0

        self.daily_tp2_hit_count = 0

        self.daily_loss_limit_hit_count = 0

        self.trade_attempt_count = 0

        # ----------------------------------------------------
        # FUNDAMENTAL / ALPHA ANALYTICS
        # ----------------------------------------------------

        self.fundamental_context_count = 0

        self.fundamental_unavailable_count = 0

        self.fundamental_rejected_count = 0

        self.multi_factor_trade_count = 0

        self.technical_fallback_trade_count = 0

    # ========================================================
    # DATA PREPARATION
    # ========================================================

    def prepare_data(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, pd.DataFrame]:

        if df.empty:
            raise ValueError("Backtest verisi boş.")

        if not isinstance(df.index, pd.MultiIndex):
            raise ValueError(
                "Backtest DataFrame MultiIndex (symbol, timestamp) kullanmalıdır."
            )

        if "symbol" not in df.index.names:
            raise ValueError("DataFrame index içinde 'symbol' bulunamadı.")

        prepared = {}

        available_symbols = set(
            df.index.get_level_values("symbol")
        )

        for symbol in self.settings.universe:

            if symbol not in available_symbols:
                continue

            symbol_df = (
                df
                .xs(symbol, level="symbol")
                .copy()
                .sort_index()
            )

            symbol_df = (
                self.indicator_engine.calculate(symbol_df)
            )

            prepared[symbol] = symbol_df

        if not prepared:
            raise ValueError("Universe içerisinde kullanılabilir sembol bulunamadı.")

        return prepared

    # ========================================================
    # TIMELINE
    # ========================================================

    def build_timeline(
        self,
        prepared_data,
    ):

        timestamps = set()

        for symbol_df in prepared_data.values():
            timestamps.update(symbol_df.index)

        return sorted(timestamps)

    # ========================================================
    # CURRENT EQUITY
    # ========================================================

    def get_current_equity(
        self,
        prices=None,
    ) -> float:

        if prices is None:
            prices = {}

        return self.portfolio.calculate_equity(prices)

    # ========================================================
    # DAILY RESET
    # ========================================================

    def reset_daily_state(
        self,
        timestamp,
        prices,
    ):

        current_day = timestamp.date()

        if self.current_day == current_day:
            return

        self.current_day = current_day

        self.daily_start_equity = (
            self.get_current_equity(prices)
        )

        self.daily_trading_done = False

        self.daily_tp1_hit = False

        self.daily_loss_limit_hit = False

    # ========================================================
    # DAILY RETURN
    # ========================================================

    def calculate_daily_return(
        self,
        equity: float,
    ) -> float:

        if self.daily_start_equity <= 0:
            return 0.0

        return (equity / self.daily_start_equity) - 1.0

    # ========================================================
    # DAILY LOSS LIMIT
    # ========================================================

    def check_daily_loss_limit(
        self,
        equity: float,
    ) -> bool:

        daily_return = self.calculate_daily_return(equity)

        if daily_return <= self.settings.max_daily_loss_pct * -1:

            if not self.daily_loss_limit_hit:
                self.daily_loss_limit_hit = True
                self.daily_loss_limit_hit_count += 1

            return True

        return False

    # ========================================================
    # COOLDOWN
    # ========================================================

    def is_in_cooldown(
        self,
        symbol,
        timestamp,
    ) -> bool:

        last_exit = self.cooldowns.get(symbol)

        if last_exit is None:
            return False

        elapsed = timestamp - last_exit
        elapsed_minutes = elapsed.total_seconds() / 60.0

        required_minutes = (
            self.settings.cooldown_bars
            * self.settings.timeframe_minutes
        )

        return elapsed_minutes < required_minutes

    # ========================================================
    # REGISTER BACKTEST POSITION RISK
    # ========================================================

    def register_position_risk(
        self,
        symbol,
        quantity,
        entry_price,
        stop_price,
    ):

        self.risk_manager.register_position_risk(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_price=stop_price,
        )

    # ========================================================
    # UNREGISTER BACKTEST POSITION RISK
    # ========================================================

    def unregister_position_risk(
        self,
        symbol,
    ):

        self.risk_manager.unregister_position(symbol)

    # ========================================================
    # SAFE FUNDAMENTAL ATTRIBUTE
    # ========================================================

    @staticmethod
    def _get_factor_value(
        factor,
        name,
        default=None,
    ):
        if factor is None:
            return default

        return getattr(factor, name, default)

    # ========================================================
    # BUILD RANKED SIGNAL CANDIDATES
    # ========================================================

    def build_ranked_candidates(
        self,
        timestamp,
        next_timestamp,
        prepared_data,
    ):
        candidates = []

        # ====================================================
        # GLOBAL MARKET REGIME (SPY)
        # ====================================================

        market_regime = None
        market_regime_result = None

        benchmark_df = prepared_data.get("SPY")

        if benchmark_df is not None:

            if timestamp in benchmark_df.index:

                benchmark_history = benchmark_df.loc[:timestamp]

                if len(benchmark_history) >= 30:

                    market_regime_result = (
                        self.market_regime_engine.evaluate(
                            benchmark_history
                        )
                    )

                    market_regime = market_regime_result.regime

        # ====================================================
        # NON-TRADABLE FILTER (SPY VE TSLA KONTENJAN KORUMASI)
        # ====================================================
        non_tradable = set(
            getattr(
                self.settings,
                "non_tradable_symbols",
                ("SPY", "TSLA"),
            )
        )

        # ====================================================
        # SCAN ALL SYMBOLS
        # ====================================================

        for symbol, symbol_df in prepared_data.items():

            # SPY ve TSLA asla satın alınmaz, kontenjan sadece High-Beta hisselere ayrılır!
            if symbol.upper() in non_tradable:
                continue

            if timestamp not in symbol_df.index:
                continue

            if next_timestamp not in symbol_df.index:
                continue

            history = symbol_df.loc[:timestamp]

            if len(history) < 52:
                continue

            # ------------------------------------------------
            # TECHNICAL SIGNAL
            # ------------------------------------------------

            signal_result = self.signal_engine.evaluate(
                symbol=symbol,
                df=history,
                market_regime=market_regime,
            )

            if signal_result.signal != Signal.BUY:
                continue

            # ------------------------------------------------
            # POINT-IN-TIME FUNDAMENTAL CONTEXT
            # ------------------------------------------------

            try:
                fundamental_context = (
                    self.fundamental_context_engine.get_context(
                        symbol=symbol,
                        as_of_date=timestamp.date(),
                    )
                )
                self.fundamental_context_count += 1

            except Exception:
                fundamental_context = None
                self.fundamental_unavailable_count += 1

            # ------------------------------------------------
            # FUNDAMENTAL FACTOR
            # ------------------------------------------------

            fundamental_factor = None

            if fundamental_context is not None:
                fundamental_factor = fundamental_context.factor

            fundamental_score = None
            data_quality_score = None

            if fundamental_factor is not None:
                fundamental_score = fundamental_factor.fundamental_score
                data_quality_score = fundamental_factor.data_quality_score

            # ------------------------------------------------
            # COMBINED ALPHA
            # ------------------------------------------------

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

            # ------------------------------------------------
            # CANDIDATE
            # ------------------------------------------------

            candidates.append(
                {
                    "symbol": symbol,
                    "signal": signal_result,
                    "history": history,
                    "next_bar": symbol_df.loc[next_timestamp],
                    "market_regime": market_regime_result,
                    "fundamental_context": fundamental_context,
                    "fundamental_factor": fundamental_factor,
                    "alpha_result": alpha_result,
                }
            )

        # ====================================================
        # RANK BY COMBINED ALPHA
        # ====================================================

        candidates.sort(
            key=lambda candidate: (
                candidate["alpha_result"].final_score,
                candidate["alpha_result"].technical_score,
                candidate["symbol"],
            ),
            reverse=True,
        )

        return candidates

    # ========================================================
    # TRY OPEN POSITION (V3.0 DYNAMIC ALPHA SIZING)
    # ========================================================

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

        # ----------------------------------------------------
        # NON-TRADABLE BLOCK
        # ----------------------------------------------------
        non_tradable = set(
            getattr(
                self.settings,
                "non_tradable_symbols",
                ("SPY", "TSLA"),
            )
        )
        if symbol.upper() in non_tradable:
            return False

        # ----------------------------------------------------
        # DAILY BLOCKS
        # ----------------------------------------------------

        if (
            self.daily_trading_done
            or self.daily_tp1_hit
            or self.daily_loss_limit_hit
        ):
            return False

        # ----------------------------------------------------
        # POSITION CHECK
        # ----------------------------------------------------

        if symbol in self.portfolio.positions:
            return False

        # ----------------------------------------------------
        # CURRENT EQUITY
        # ----------------------------------------------------

        equity = self.get_current_equity(prices)

        if equity <= 0:
            return False

        # ----------------------------------------------------
        # DAILY LOSS
        # ----------------------------------------------------

        if self.check_daily_loss_limit(equity):
            return False

        # ----------------------------------------------------
        # COOLDOWN
        # ----------------------------------------------------

        if self.is_in_cooldown(symbol, timestamp):
            return False

        # ----------------------------------------------------
        # SIGNAL
        # ----------------------------------------------------

        signal = signal_result

        if signal is None:
            signal = self.signal_engine.evaluate(
                symbol=symbol,
                df=history,
            )

        if signal.signal != Signal.BUY:
            return False

        # ----------------------------------------------------
        # COMBINED ALPHA
        # ----------------------------------------------------

        if alpha_result is None:

            fundamental_context = None
            fundamental_factor = None
            fundamental_score = None
            data_quality_score = None

            try:
                fundamental_context = (
                    self.fundamental_context_engine.get_context(
                        symbol=symbol,
                        as_of_date=timestamp.date(),
                    )
                )
                self.fundamental_context_count += 1
                fundamental_factor = fundamental_context.factor

                if fundamental_factor is not None:
                    fundamental_score = fundamental_factor.fundamental_score
                    data_quality_score = fundamental_factor.data_quality_score

            except Exception:
                fundamental_context = None
                fundamental_factor = None
                fundamental_score = None
                data_quality_score = None
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

        # ----------------------------------------------------
        # ENTRY
        # ----------------------------------------------------

        entry_price = float(next_bar["open"])

        if entry_price <= 0:
            return False

        # ----------------------------------------------------
        # ATR
        # ----------------------------------------------------

        atr_value = history.iloc[-1]["atr"]

        if pd.isna(atr_value):
            return False

        atr = float(atr_value)

        if atr <= 0:
            return False

        # ----------------------------------------------------
        # POSITION SIZING (WITH DYNAMIC ALPHA BOOST)
        # ----------------------------------------------------

        # Dinamik Alpha Risk Çarpanı:
        # Eğer Alpha skoru yüksekse (örn: 85+), efektif equity'yi ölçekleyerek
        # PositionSizer'ın daha yüksek mermi sürmesini sağlıyoruz (Nakit sınırını aşmadan).
        sizing_equity = equity
        use_dynamic_risk = bool(getattr(self.settings, "use_dynamic_risk", False))
        
        if use_dynamic_risk and alpha_result is not None:
            high_alpha_thresh = float(getattr(self.settings, "high_alpha_threshold", 85.0))
            base_risk_pct = float(getattr(self.settings, "max_risk_per_trade_pct", 0.0225))
            high_risk_pct = float(getattr(self.settings, "high_alpha_risk_pct", 0.0325))
            
            if alpha_result.final_score >= high_alpha_thresh and base_risk_pct > 0:
                boost_factor = high_risk_pct / base_risk_pct
                sizing_equity = equity * boost_factor

        try:
            position_size = self.position_sizer.calculate(
                symbol=symbol,
                entry_price=entry_price,
                atr=atr,
                equity=sizing_equity,
                available_cash=self.portfolio.cash,
            )

        except ValueError:
            return False

        quantity = position_size.quantity
        stop_price = position_size.stop_price
        target_price = position_size.target_price

        use_fixed_target = bool(
            getattr(self.settings, "use_fixed_target", True)
        )

        if not use_fixed_target:
            target_price = None

        if quantity <= 0:
            return False

        # ----------------------------------------------------
        # CENTRAL RISK APPROVAL
        # ----------------------------------------------------

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

        # ====================================================
        # ALPHA / FUNDAMENTAL METADATA
        # ====================================================

        alpha_mode = (
            getattr(alpha_result, "alpha_mode", None)
            or (
                "MULTI_FACTOR"
                if alpha_result.fundamental_score is not None
                else "TECHNICAL_FALLBACK"
            )
        )

        fundamental_available = getattr(
            alpha_result, "fundamental_available", None
        )

        if fundamental_available is None:
            fundamental_available = (
                alpha_result.fundamental_score is not None
            )

        fundamental_factor = None

        if (
            fundamental_available
            and alpha_result.fundamental_score is not None
        ):
            try:
                context = self.fundamental_context_engine.get_context(
                    symbol=symbol,
                    as_of_date=history.index[-1].date(),
                )
                fundamental_factor = context.factor
            except Exception:
                fundamental_factor = None

        # ----------------------------------------------------
        # ACCOUNT EXPOSURE
        # ----------------------------------------------------

        position_value = float(position_size.position_value)

        exposure_pct = (
            (position_value / equity)
            if equity > 0
            else 0.0
        )

        # ----------------------------------------------------
        # ENTRY METRICS
        # ----------------------------------------------------

        last_bar = history.iloc[-1]

        entry_metrics = {
            "rsi": (
                float(last_bar["rsi"])
                if ("rsi" in last_bar and pd.notna(last_bar["rsi"]))
                else 0.0
            ),
            "volume_ratio": (
                float(last_bar["volume_ratio"])
                if ("volume_ratio" in last_bar and pd.notna(last_bar["volume_ratio"]))
                else 0.0
            ),
            "macd": (
                float(last_bar["macd"])
                if ("macd" in last_bar and pd.notna(last_bar["macd"]))
                else 0.0
            ),
            "macd_histogram": (
                float(last_bar["macd_histogram"])
                if ("macd_histogram" in last_bar and pd.notna(last_bar["macd_histogram"]))
                else 0.0
            ),
            "price_vs_ema50": (
                float(last_bar["price_vs_ema50"])
                if ("price_vs_ema50" in last_bar and pd.notna(last_bar["price_vs_ema50"]))
                else 0.0
            ),
            "volume_breakout": (
                bool(last_bar["volume_breakout"])
                if ("volume_breakout" in last_bar and pd.notna(last_bar["volume_breakout"]))
                else False
            ),
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

        # ----------------------------------------------------
        # OPEN PORTFOLIO POSITION
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # REGISTER RISK
        # ----------------------------------------------------

        self.register_position_risk(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_price=stop_price,
        )

        return True

    # ========================================================
    # MANAGE POSITION V3.0 (OFFSET BE & PARABOLIC LOCK)
    # ========================================================

    def manage_position(
        self,
        symbol,
        timestamp,
        bar,
    ) -> bool:
        """
        V3.0 Position Management:
        - +0.70R -> Break Even + 0.20R Profit Offset (Bedava kâr kilidi)
        - +1.20R -> Lock +0.65R
        - +1.50R -> ATR Trailing
        - Parabolic Tightening: RSI >= 75 olduğunda ATR çarpanını 0.85x'e daraltır!
        """

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

        initial_risk = (
            position.entry_price - position.initial_stop_price
        )

        if initial_risk <= 0:
            return False

        current_stop = float(position.stop_price)

        # ====================================================
        # 1. EXISTING STOP CHECK
        # ====================================================

        stop_hit = (low <= current_stop)

        # ====================================================
        # 2. OPTIONAL FIXED TARGET
        # ====================================================

        use_fixed_target = bool(
            getattr(self.settings, "use_fixed_target", False)
        )

        target_hit = False

        if use_fixed_target and position.target_price is not None:
            target_hit = (high >= float(position.target_price))

        # ====================================================
        # AMBIGUOUS BAR
        # ====================================================

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

        # ====================================================
        # STOP
        # ====================================================

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

        # ====================================================
        # FIXED TARGET
        # ====================================================

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

        # ====================================================
        # UPDATE POSITION STATE
        # ====================================================

        self.portfolio.update_position_state(
            symbol=symbol,
            current_price=close,
        )

        position = self.portfolio.positions[symbol]

        if high > position.highest_price:
            position.highest_price = high

        position.current_r = (
            close - position.entry_price
        ) / initial_risk

        high_r = (
            high - position.entry_price
        ) / initial_risk

        # ====================================================
        # ATR & RSI EXTRACTION
        # ====================================================

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

        # ====================================================
        # STOP CANDIDATE
        # ====================================================

        new_stop = position.stop_price
        management_reason = None

        # ====================================================
        # 1. BREAK EVEN (+0.20R OFFSET)
        # ====================================================

        break_even_at_r = float(
            getattr(self.settings, "break_even_at_r", 0.75)
        )
        break_even_offset_r = float(
            getattr(self.settings, "break_even_offset_r", 0.20)
        )

        be_stop = position.entry_price + (initial_risk * break_even_offset_r)

        if high_r >= break_even_at_r and position.stop_price < be_stop:
            new_stop = max(new_stop, be_stop)
            management_reason = "BREAK_EVEN_PLUS"

        # ====================================================
        # 2. PROFIT LOCK
        # ====================================================

        lock_profit_at_r = float(
            getattr(self.settings, "lock_profit_at_r", 1.2)
        )
        lock_profit_r = float(
            getattr(self.settings, "lock_profit_r", 0.65)
        )

        lock_stop = position.entry_price + (initial_risk * lock_profit_r)

        if high_r >= lock_profit_at_r and position.stop_price < lock_stop:
            new_stop = max(new_stop, lock_stop)
            management_reason = "PROFIT_LOCK"

        # ====================================================
        # 3. ATR TRAILING & PARABOLIC TIGHTENING
        # ====================================================

        trailing_start_at_r = float(
            getattr(self.settings, "trailing_start_at_r", 1.5)
        )
        trailing_atr_multiplier = float(
            getattr(self.settings, "trailing_atr_multiplier", 1.4)
        )

        # Parabolik Sıkılaştırma: Eğer RSI >= 75 ise veya kâr +3.0R'yi geçtiyse
        # stop mesafesini daraltarak zirvedeki köpüğü cebe indir!
        parabolic_rsi_threshold = float(
            getattr(self.settings, "parabolic_rsi_threshold", 75.0)
        )
        parabolic_atr_multiplier = float(
            getattr(self.settings, "parabolic_atr_multiplier", 0.85)
        )

        active_atr_mult = trailing_atr_multiplier
        is_parabolic = (
            (bar_rsi is not None and bar_rsi >= parabolic_rsi_threshold)
            or high_r >= 3.0
        )

        if is_parabolic and high_r >= 1.0:
            active_atr_mult = parabolic_atr_multiplier

        if (
            (high_r >= trailing_start_at_r or (is_parabolic and high_r >= 1.0))
            and atr is not None
            and atr > 0
        ):
            trailing_stop = position.highest_price - (atr * active_atr_mult)
            if trailing_stop > new_stop:
                new_stop = trailing_stop
                management_reason = (
                    "PARABOLIC_TRAILING" if is_parabolic else "ATR_TRAILING"
                )

        # ====================================================
        # STOP UPDATE
        # ====================================================

        if new_stop > position.stop_price:

            updated = self.portfolio.update_stop_price(
                symbol=symbol,
                new_stop_price=new_stop,
            )

            if updated:
                current_position = self.portfolio.positions[symbol]

                # UPDATE RISK REGISTRY
                self.unregister_position_risk(symbol)

                # Eğer yeni stop giriş fiyatının üzerindeyse (kâr garantilendiyse),
                # stop_price > entry_price olacağı için RiskManager'da açık risk 0 olarak görünür
                # ve yeni işlemlere kontenjan/risk alanı açılır!
                self.register_position_risk(
                    symbol=symbol,
                    quantity=current_position.quantity,
                    entry_price=current_position.entry_price,
                    stop_price=current_position.stop_price,
                )

                current_position.entry_metrics["last_stop_management"] = management_reason
                current_position.entry_metrics["last_stop_update_r"] = current_position.stop_r

        return False

    # ========================================================
    # DATE RANGE
    # ========================================================

    def filter_date_range(
        self,
        prepared_data,
        start_date=None,
        end_date=None,
    ):

        if start_date is None and end_date is None:
            return prepared_data

        filtered = {}

        for symbol, symbol_df in prepared_data.items():

            data = symbol_df

            if start_date is not None:
                start = pd.Timestamp(start_date)
                if data.index.tz is not None:
                    if start.tzinfo is None:
                        start = start.tz_localize(data.index.tz)
                    else:
                        start = start.tz_convert(data.index.tz)
                data = data.loc[data.index >= start]

            if end_date is not None:
                end = pd.Timestamp(end_date)
                if data.index.tz is not None:
                    if end.tzinfo is None:
                        end = end.tz_localize(data.index.tz)
                    else:
                        end = end.tz_convert(data.index.tz)
                data = data.loc[data.index <= end]

            if not data.empty:
                filtered[symbol] = data

        return filtered

    # ========================================================
    # RUN
    # ========================================================

    def run(
        self,
        df: pd.DataFrame,
        start_date=None,
        end_date=None,
    ):

        self._reset_runtime_state()

        prepared = self.prepare_data(df)

        prepared = self.filter_date_range(
            prepared,
            start_date=start_date,
            end_date=end_date,
        )

        if not prepared:
            raise ValueError(
                "Belirtilen tarih aralığında backtest verisi bulunamadı."
            )

        timeline = self.build_timeline(prepared)

        if len(timeline) < 3:
            raise ValueError("Backtest için yeterli veri bulunmuyor.")

        print(f"[BACKTEST] {len(timeline)} zaman noktası işlenecek.")

        # ====================================================
        # MAIN LOOP
        # ====================================================

        for i in range(1, len(timeline) - 1):

            timestamp = timeline[i]
            next_timestamp = timeline[i + 1]

            # CURRENT PRICES
            current_prices = {}

            for symbol, symbol_df in prepared.items():
                if timestamp not in symbol_df.index:
                    continue
                current_bar = symbol_df.loc[timestamp]
                current_prices[symbol] = float(current_bar["close"])

            # DAILY RESET
            self.reset_daily_state(
                timestamp=timestamp,
                prices=current_prices,
            )

            # MANAGE OPEN POSITIONS
            for symbol, symbol_df in prepared.items():
                if timestamp not in symbol_df.index:
                    continue
                current_bar = symbol_df.loc[timestamp]
                self.manage_position(
                    symbol=symbol,
                    timestamp=timestamp,
                    bar=current_bar,
                )

            # EQUITY
            current_equity = self.get_current_equity(current_prices)
            daily_return = self.calculate_daily_return(current_equity)

            # DAILY LOSS
            self.check_daily_loss_limit(current_equity)

            # DAILY TP2
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

            # DAILY TP1
            elif (
                getattr(self.settings, "daily_tp1_enabled", True)
                and daily_return >= self.settings.daily_tp1_pct
                and not self.daily_tp1_hit
            ):
                self.daily_tp1_hit = True
                self.daily_tp1_hit_count += 1

            # NEW POSITIONS
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

                    micro_account_mode = bool(
                        getattr(self.settings, "micro_account_mode", False)
                    )

                    if micro_account_mode:
                        max_open_positions = int(
                            getattr(self.settings, "micro_max_open_positions", 1)
                        )
                    else:
                        max_open_positions = int(
                            getattr(self.settings, "max_open_positions", 2)
                        )

                    if len(self.portfolio.positions) >= max_open_positions:
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

            # EQUITY SNAPSHOT
            self.portfolio.record_equity(
                timestamp=timestamp,
                prices=current_prices,
                daily_start_equity=self.daily_start_equity,
                daily_return_pct=daily_return * 100.0,
                daily_loss_limit_hit=self.daily_loss_limit_hit,
                daily_tp1_hit=self.daily_tp1_hit,
                daily_tp2_hit=self.daily_trading_done,
            )

        # ====================================================
        # FORCE CLOSE
        # ====================================================

        final_timestamp = timeline[-1]
        final_prices = {}

        for symbol, symbol_df in prepared.items():
            if final_timestamp not in symbol_df.index:
                continue
            final_prices[symbol] = float(
                symbol_df.loc[final_timestamp, "close"]
            )

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

        # FINAL EQUITY
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

        # ====================================================
        # METRICS
        # ====================================================

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