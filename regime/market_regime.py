from dataclasses import dataclass
from enum import Enum

import pandas as pd


# ============================================================
# MARKET REGIME
# ============================================================

class MarketRegime(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    UNKNOWN = "UNKNOWN"


# ============================================================
# REGIME RESULT
# ============================================================

@dataclass
class MarketRegimeResult:
    regime: MarketRegime

    trend_score: float
    momentum_score: float
    volatility_score: float

    reason: str


# ============================================================
# MARKET REGIME ENGINE
# ============================================================

class MarketRegimeEngine:

    def __init__(self, settings):
        self.settings = settings

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _safe_float(value):

        if pd.isna(value):
            return None

        try:
            return float(value)

        except (TypeError, ValueError):
            return None

    # ========================================================
    # EVALUATE
    # ========================================================

    def evaluate(
        self,
        df: pd.DataFrame,
    ) -> MarketRegimeResult:

        # ----------------------------------------------------
        # DATA LENGTH
        # ----------------------------------------------------

        if df is None or len(df) < 30:

            return MarketRegimeResult(
                regime=MarketRegime.UNKNOWN,
                trend_score=0.0,
                momentum_score=0.0,
                volatility_score=0.0,
                reason="Insufficient data.",
            )

        # ----------------------------------------------------
        # REQUIRED COLUMNS
        # ----------------------------------------------------

        required_columns = [
            "close",
            "ema_9",
            "ema_21",
            "atr",
            "return_3",
            "return_6",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:

            return MarketRegimeResult(
                regime=MarketRegime.UNKNOWN,
                trend_score=0.0,
                momentum_score=0.0,
                volatility_score=0.0,
                reason=(
                    "Missing indicator: "
                    + missing_columns[0]
                ),
            )

        # ----------------------------------------------------
        # LAST BAR
        # ----------------------------------------------------

        last = df.iloc[-1]

        close = self._safe_float(last["close"])
        ema_9 = self._safe_float(last["ema_9"])
        ema_21 = self._safe_float(last["ema_21"])
        atr = self._safe_float(last["atr"])
        return_3 = self._safe_float(last["return_3"])
        return_6 = self._safe_float(last["return_6"])

        values = [
            close,
            ema_9,
            ema_21,
            atr,
            return_3,
            return_6,
        ]

        if any(value is None for value in values):

            return MarketRegimeResult(
                regime=MarketRegime.UNKNOWN,
                trend_score=0.0,
                momentum_score=0.0,
                volatility_score=0.0,
                reason="Indicator values are not ready.",
            )

        # ====================================================
        # TREND SCORE
        # ====================================================

        trend_score = 0.0

        if close > ema_21:
            trend_score += 1.0

        if ema_9 > ema_21:
            trend_score += 1.0

        # ====================================================
        # MOMENTUM SCORE
        # ====================================================

        momentum_score = 0.0

        if return_3 > 0:
            momentum_score += 1.0

        if return_6 > 0:
            momentum_score += 1.0

        # ====================================================
        # VOLATILITY
        # ====================================================

        volatility_ratio = (
            atr / close
            if close > 0
            else 0.0
        )

        volatility_score = volatility_ratio * 100.0

        # ====================================================
        # HIGH VOLATILITY
        # ====================================================

        if volatility_ratio >= 0.01:

            return MarketRegimeResult(
                regime=MarketRegime.HIGH_VOLATILITY,
                trend_score=trend_score,
                momentum_score=momentum_score,
                volatility_score=volatility_score,
                reason=(
                    "ATR relative to price indicates "
                    "high volatility."
                ),
            )

        # ====================================================
        # BULL
        # ====================================================

        if (
            trend_score >= 2.0
            and momentum_score >= 1.0
        ):

            return MarketRegimeResult(
                regime=MarketRegime.BULL,
                trend_score=trend_score,
                momentum_score=momentum_score,
                volatility_score=volatility_score,
                reason=(
                    "Price/EMA trend is bullish "
                    "with positive momentum."
                ),
            )

        # ====================================================
        # BEAR
        # ====================================================

        if (
            trend_score == 0.0
            and momentum_score == 0.0
            and close < ema_21
            and ema_9 < ema_21
        ):

            return MarketRegimeResult(
                regime=MarketRegime.BEAR,
                trend_score=trend_score,
                momentum_score=momentum_score,
                volatility_score=volatility_score,
                reason=(
                    "Price and EMA trend are bearish "
                    "with negative momentum."
                ),
            )

        # ====================================================
        # SIDEWAYS
        # ====================================================

        return MarketRegimeResult(
            regime=MarketRegime.SIDEWAYS,
            trend_score=trend_score,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            reason=(
                "Trend and momentum are not "
                "strong enough for a directional regime."
            ),
        )