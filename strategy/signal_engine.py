from dataclasses import dataclass
from enum import Enum
import pandas as pd
from strategy.pattern_engine import PatternEngine

# ============================================================
# SIGNAL TYPES
# ============================================================

class Signal(Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    REJECT = "REJECT"

# ============================================================
# SIGNAL RESULT
# ============================================================

@dataclass
class SignalResult:
    symbol: str
    signal: Signal
    score: int
    reasons: list[str]
    regime: str = "UNKNOWN"

# ============================================================
# SIGNAL ENGINE (NO FEAR REVISION: ANTI-WHIPSAW & ANTI-FOMO)
# ============================================================

class SignalEngine:

    def __init__(self, settings):
        self.settings = settings
        self.pattern_engine = PatternEngine(settings)

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _rsi_score(rsi: float) -> float:
        if rsi < 40 or rsi > 85: 
            return 0.0
        if 50 <= rsi <= 70:
            return 10.0
        if 40 <= rsi < 50: 
            return 8.0
        if 70 < rsi <= 85: 
            return 8.0
        return 5.0

    @staticmethod
    def _volume_score(volume_ratio: float) -> float:
        if volume_ratio < 0.8: return 0.0
        if volume_ratio > 2.5: return 15.0 
        if 1.0 <= volume_ratio <= 2.0: return 10.0
        if 0.8 <= volume_ratio < 1.0: return 6.0
        return 7.0

    @staticmethod
    def _ema_score(ema_gap_pct: float) -> float:
        if ema_gap_pct <= 0: return 0.0
        normalized = ema_gap_pct / 0.003
        return SignalEngine._clamp(normalized, 0.0, 1.0) * 10.0

    @staticmethod
    def _macd_score(macd_strength: float) -> float:
        if macd_strength <= 0: return 0.0
        normalized = macd_strength / 0.50
        return SignalEngine._clamp(normalized, 0.0, 1.0) * 10.0

    def evaluate(self, symbol: str, df: pd.DataFrame, market_regime=None) -> SignalResult:

        regime_name = "UNKNOWN"
        if market_regime is not None:
            if hasattr(market_regime, "value"):
                regime_name = str(market_regime.value).upper()
            elif hasattr(market_regime, "regime"):
                regime_value = market_regime.regime
                if hasattr(regime_value, "value"):
                    regime_name = str(regime_value.value).upper()
                else:
                    regime_name = str(regime_value).upper()
            else:
                regime_name = str(market_regime).upper()

        if df is None or len(df) < 52: 
            return SignalResult(
                symbol=symbol, signal=Signal.REJECT, score=0,
                reasons=["Insufficient data (Need 52+ bars)"],
                regime=regime_name,
            )

        required_columns = [
            "macd", "macd_signal", "ema_9", "ema_21", "ema_50", "sma_20", 
            "ema_5", "ema_7", "price_vs_ema50", "ema_gap_pct", "rsi",
            "volume_ratio", "volume_breakout", "macd_histogram", "macd_strength",
            "open", "high", "low", "close"
        ]

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return SignalResult(
                symbol=symbol, signal=Signal.REJECT, score=0,
                reasons=["Missing indicator: " + missing_columns[0]], regime=regime_name,
            )

        last = df.iloc[-1]
        previous = df.iloc[-2]

        macd = float(last["macd"])
        macd_signal = float(last["macd_signal"])
        previous_macd = float(previous["macd"])
        previous_macd_signal = float(previous["macd_signal"])

        ema_9 = float(last["ema_9"])
        ema_21 = float(last["ema_21"])
        
        price_vs_ema50 = float(last["price_vs_ema50"])
        
        rsi = float(last["rsi"])
        volume_ratio = float(last["volume_ratio"])
        volume_breakout = bool(last["volume_breakout"])
        ema_gap_pct = float(last["ema_gap_pct"])
        macd_strength = float(last["macd_strength"])

        open_price = float(last["open"])
        high_price = float(last["high"])
        low_price = float(last["low"])
        close_price = float(last["close"])

        pattern_result = self.pattern_engine.evaluate(df)
        has_pattern = (pattern_result.hammer or pattern_result.engulfing or pattern_result.bull_flag)

        # ====================================================
        # 🛡️ BOUCLIERS DE SURVIE (SURVIVAL SHIELDS)
        # ====================================================
        
        # 1. Anti-Whipsaw Shield (Résout le problème du Mercredi)
        # Si la mèche haute est énorme, c'est un faux signal d'achat créé par les news.
        candle_range = high_price - low_price
        upper_wick = high_price - max(open_price, close_price)
        whipsaw_rejection = False
        if candle_range > 0 and (upper_wick / candle_range) > 0.45:
            whipsaw_rejection = True

        # 2. Anti-FOMO Shield (Résout le "Syndrome Tesla")
        # Si le prix est éloigné de plus de 5% de la moyenne mobile (EMA), c'est du FOMO.
        fomo_extreme = ema_gap_pct > 0.05 

        is_safe = not whipsaw_rejection and not fomo_extreme

        # ====================================================
        # TREND & TRIGGERS
        # ====================================================
        macd_bullish = (macd > macd_signal)
        ema_bullish = (ema_9 > ema_21)
        
        mid_trend_bullish = (price_vs_ema50 > 0)
        is_trend_ok = mid_trend_bullish

        macd_cross = (previous_macd <= previous_macd_signal and macd_bullish)
        ema_cross = (float(previous["ema_9"]) <= float(previous["ema_21"]) and ema_bullish)

        is_trigger = (macd_cross or ema_cross or volume_breakout or has_pattern)

        # ====================================================
        # FILTERS
        # ====================================================
        rsi_ok = (40 <= rsi <= 85)
        volume_ok = (0.8 <= volume_ratio <= 4.0)

        # ====================================================
        # TECHNICAL SCORE
        # ====================================================
        score = 0.0

        if macd_bullish: score += 10.0
        if ema_bullish: score += 10.0
        if mid_trend_bullish: score += 10.0
        if macd_cross: score += 15.0
        if ema_cross: score += 15.0
        if volume_breakout: score += 10.0

        score += pattern_result.score
        score += self._macd_score(macd_strength)
        score += self._ema_score(ema_gap_pct)
        score += self._rsi_score(rsi)
        score += self._volume_score(volume_ratio)

        score = int(round(self._clamp(score, 0.0, 100.0)))

        # ====================================================
        # REASONS & DECISION
        # ====================================================
        reasons = []

        if not is_trend_ok: reasons.append("Trend not fully bullish (Price below 50 EMA).")
        if not is_trigger: reasons.append("No MACD/EMA crossover, Volume Breakout, or Pattern trigger.")
        if whipsaw_rejection: reasons.append("🛡️ ANTI-WHIPSAW: Rejet violent des vendeurs détecté (Mèche haute énorme).")
        if fomo_extreme: reasons.append(f"🛡️ ANTI-FOMO: Prix trop éloigné de l'EMA ({ema_gap_pct*100:.1f}%).")
        if not rsi_ok: reasons.append(f"RSI out of bounds: {rsi:.1f}")
        if not volume_ok: reasons.append(f"Volume out of bounds: {volume_ratio:.2f}x")
        if has_pattern: reasons.append(f"Formasyon: {pattern_result.reason}")

        reasons.append(f"Market regime={regime_name}")
        reasons.append(f"Technical score={score}")

        if (
            is_trend_ok
            and is_trigger
            and is_safe
            and rsi_ok
            and volume_ok
            and regime_name != "BEAR"
            and score >= self.settings.minimum_buy_score
        ):
            return SignalResult(
                symbol=symbol,
                signal=Signal.BUY,
                score=score,
                reasons=["Swing Trend confirmed.", "Trigger confirmed."] + reasons[-2:],
                regime=regime_name,
            )

        reasons.append(f"Final technical score={score}")
        if regime_name == "BEAR":
            reasons.append("Long entry blocked by BEAR market regime.")

        return SignalResult(
            symbol=symbol, signal=Signal.REJECT, score=score, reasons=reasons, regime=regime_name,
        )