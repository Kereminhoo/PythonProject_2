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
# MARKET REGIME ENGINE (SWING TRADING REVISION)
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
        # Swing trading needs at least 50 bars to judge the regime properly
        if df is None or len(df) < 50:

            return MarketRegimeResult(
                regime=MarketRegime.UNKNOWN,
                trend_score=0.0,
                momentum_score=0.0,
                volatility_score=0.0,
                reason="Insufficient data. Need at least 50 bars.",
            )

        # ----------------------------------------------------
        # REQUIRED COLUMNS
        # ----------------------------------------------------

        # We now rely on longer-term EMAs/SMAs calculated in indicator_engine
        required_columns = [
            "close",
            "ema_21",
            "ema_50",
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
        ema_21 = self._safe_float(last["ema_21"])
        ema_50 = self._safe_float(last["ema_50"])
        atr = self._safe_float(last["atr"])
        return_3 = self._safe_float(last["return_3"])
        return_6 = self._safe_float(last["return_6"])

        values = [
            close,
            ema_21,
            ema_50,
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

        if close > ema_50:
            trend_score += 1.0

        if ema_21 > ema_50:
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
        # HIGH VOLATILITY (ADJUSTED FOR DAILY BARS)
        # ====================================================
        
        # 0.04 = 4% daily ATR. If SPY moves 4% a day, the market is in panic mode.
        if volatility_ratio >= 0.04:

            return MarketRegimeResult(
                regime=MarketRegime.HIGH_VOLATILITY,
                trend_score=trend_score,
                momentum_score=momentum_score,
                volatility_score=volatility_score,
                reason=(
                    "ATR relative to price (>4%) indicates "
                    "extreme high volatility panic mode."
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
                    "Price > 50 EMA and 21 EMA > 50 EMA. "
                    "Macro trend is bullish."
                ),
            )

        # ====================================================
        # BEAR
        # ====================================================

        if (
            trend_score == 0.0
            and momentum_score <= 1.0
            and close < ema_50
            and ema_21 < ema_50
        ):

            return MarketRegimeResult(
                regime=MarketRegime.BEAR,
                trend_score=trend_score,
                momentum_score=momentum_score,
                volatility_score=volatility_score,
                reason=(
                    "Price < 50 EMA and 21 EMA < 50 EMA. "
                    "Macro trend is bearish."
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
                "Trend and momentum are mixed. "
                "Market is in a sideways or transition phase."
            ),
        )