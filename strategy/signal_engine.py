from dataclasses import dataclass
from enum import Enum

import pandas as pd


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
# SIGNAL ENGINE
# ============================================================

class SignalEngine:

    def __init__(self, settings):
        self.settings = settings

    # ========================================================
    # SCORE HELPERS
    # ========================================================

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:

        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )

    @staticmethod
    def _rsi_score(
        rsi: float,
    ) -> float:

        if rsi < 50 or rsi > 70:
            return 0.0

        if 60 <= rsi <= 68:
            return 10.0

        if 55 <= rsi < 60:
            return 8.0

        if 68 < rsi <= 70:
            return 8.0

        return 5.0

    @staticmethod
    def _volume_score(
        volume_ratio: float,
    ) -> float:

        if volume_ratio < 0.8:
            return 0.0

        if volume_ratio > 2.5:
            return 2.0

        if 1.0 <= volume_ratio <= 2.0:
            return 10.0

        if 0.8 <= volume_ratio < 1.0:
            return 6.0

        return 7.0

    @staticmethod
    def _vwap_score(
        price_vs_vwap: float,
    ) -> float:

        if price_vs_vwap <= 0:
            return 0.0

        normalized = (
            price_vs_vwap
            / 0.005
        )

        return (
            SignalEngine._clamp(
                normalized,
                0.0,
                1.0,
            )
            * 10.0
        )

    @staticmethod
    def _ema_score(
        ema_gap_pct: float,
    ) -> float:

        if ema_gap_pct <= 0:
            return 0.0

        normalized = (
            ema_gap_pct
            / 0.003
        )

        return (
            SignalEngine._clamp(
                normalized,
                0.0,
                1.0,
            )
            * 10.0
        )

    @staticmethod
    def _macd_score(
        macd_strength: float,
    ) -> float:

        if macd_strength <= 0:
            return 0.0

        normalized = (
            macd_strength
            / 0.50
        )

        return (
            SignalEngine._clamp(
                normalized,
                0.0,
                1.0,
            )
            * 10.0
        )

    # ========================================================
    # EVALUATE
    # ========================================================

    def evaluate(
        self,
        symbol: str,
        df: pd.DataFrame,
        market_regime=None,
    ) -> SignalResult:

        # ----------------------------------------------------
        # MARKET REGIME
        # ----------------------------------------------------
        #
        # Rejim burada SADECE metadata/decision filter olarak
        # kullanılır.
        #
        # Rejim adjustment artık score'a eklenmez.
        # Bu adjustment CombinedAlphaEngine tarafından
        # tam olarak bir kez uygulanır.
        #

        regime_name = "UNKNOWN"

        if market_regime is not None:

            if hasattr(
                market_regime,
                "value",
            ):
                regime_name = str(
                    market_regime.value
                ).upper()

            elif hasattr(
                market_regime,
                "regime",
            ):
                regime_value = (
                    market_regime.regime
                )

                if hasattr(
                    regime_value,
                    "value",
                ):
                    regime_name = str(
                        regime_value.value
                    ).upper()
                else:
                    regime_name = str(
                        regime_value
                    ).upper()

            else:
                regime_name = str(
                    market_regime
                ).upper()

        # ----------------------------------------------------
        # BASIC DATA VALIDATION
        # ----------------------------------------------------

        if df is None or len(df) < 30:

            return SignalResult(
                symbol=symbol,
                signal=Signal.REJECT,
                score=0,
                reasons=[
                    "Insufficient data"
                ],
                regime=regime_name,
            )

        required_columns = [
            "macd",
            "macd_signal",
            "ema_9",
            "ema_21",
            "ema_gap_pct",
            "rsi",
            "volume_ratio",
            "macd_histogram",
            "macd_strength",
            "price_vs_vwap",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:

            return SignalResult(
                symbol=symbol,
                signal=Signal.REJECT,
                score=0,
                reasons=[
                    "Missing indicator: "
                    + column
                    for column in missing_columns
                ],
                regime=regime_name,
            )

        last = df.iloc[-1]
        previous = df.iloc[-2]

        values = [
            last[column]
            for column in required_columns
        ]

        if any(
            pd.isna(value)
            for value in values
        ):

            return SignalResult(
                symbol=symbol,
                signal=Signal.REJECT,
                score=0,
                reasons=[
                    "Indicators not ready"
                ],
                regime=regime_name,
            )

        # ====================================================
        # VALUES
        # ====================================================

        macd = float(last["macd"])
        macd_signal = float(last["macd_signal"])

        previous_macd = float(
            previous["macd"]
        )

        previous_macd_signal = float(
            previous["macd_signal"]
        )

        ema_9 = float(last["ema_9"])
        ema_21 = float(last["ema_21"])

        previous_ema_9 = float(
            previous["ema_9"]
        )

        previous_ema_21 = float(
            previous["ema_21"]
        )

        rsi = float(last["rsi"])
        volume_ratio = float(
            last["volume_ratio"]
        )

        price_vs_vwap = float(
            last["price_vs_vwap"]
        )

        ema_gap_pct = float(
            last["ema_gap_pct"]
        )

        macd_strength = float(
            last["macd_strength"]
        )

        # ====================================================
        # TREND
        # ====================================================

        macd_bullish = (
            macd > macd_signal
        )

        ema_bullish = (
            ema_9 > ema_21
        )

        vwap_bullish = (
            price_vs_vwap > 0
        )

        is_trend_ok = (
            macd_bullish
            and ema_bullish
            and vwap_bullish
        )

        # ====================================================
        # TRIGGER
        # ====================================================

        macd_cross = (
            previous_macd
            <= previous_macd_signal
            and macd_bullish
        )

        ema_cross = (
            previous_ema_9
            <= previous_ema_21
            and ema_bullish
        )

        is_trigger = (
            macd_cross
            or ema_cross
        )

        # ====================================================
        # FILTERS
        # ====================================================

        rsi_ok = (
            50
            <= rsi
            <= 70
        )

        volume_ok = (
            0.8
            <= volume_ratio
            <= 2.5
        )

        # ====================================================
        # TECHNICAL SCORE
        # ====================================================

        score = 0.0

        if macd_bullish:
            score += 10.0

        if ema_bullish:
            score += 10.0

        if vwap_bullish:
            score += (
                self._vwap_score(
                    price_vs_vwap
                )
            )

        if macd_cross:
            score += 15.0

        if ema_cross:
            score += 15.0

        score += (
            self._macd_score(
                macd_strength
            )
        )

        score += (
            self._ema_score(
                ema_gap_pct
            )
        )

        score += (
            self._rsi_score(
                rsi
            )
        )

        score += (
            self._volume_score(
                volume_ratio
            )
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # NO MARKET REGIME ADJUSTMENT HERE.
        #
        # SignalEngine outputs pure technical alpha.
        # ----------------------------------------------------

        score = int(
            round(
                self._clamp(
                    score,
                    0.0,
                    100.0,
                )
            )
        )

        # ====================================================
        # REASONS
        # ====================================================

        reasons = []

        if not is_trend_ok:

            reasons.append(
                "Trend not fully bullish."
            )

        if not is_trigger:

            reasons.append(
                "No MACD/EMA crossover trigger."
            )

        if not rsi_ok:

            reasons.append(
                f"RSI out of bounds: {rsi:.1f}"
            )

        if not volume_ok:

            reasons.append(
                f"Volume out of bounds: "
                f"{volume_ratio:.2f}x"
            )

        reasons.append(
            f"Market regime={regime_name}"
        )

        reasons.append(
            f"Technical score={score}"
        )

        # ====================================================
        # FINAL DECISION
        # ====================================================

        if (
            is_trend_ok
            and is_trigger
            and rsi_ok
            and volume_ok
            and regime_name != "BEAR"
            and score >= self.settings.minimum_buy_score
        ):

            return SignalResult(
                symbol=symbol,
                signal=Signal.BUY,
                score=score,
                reasons=[
                    "Trend confirmed.",
                    "Trigger confirmed.",
                    f"RSI={rsi:.1f}",
                    f"Volume={volume_ratio:.2f}x",
                    f"Market regime={regime_name}",
                    f"Technical score={score}",
                ],
                regime=regime_name,
            )

        # ----------------------------------------------------
        # REJECT
        # ----------------------------------------------------

        reasons.append(
            f"Final technical score={score}"
        )

        if regime_name == "BEAR":

            reasons.append(
                "Long entry blocked by BEAR market regime."
            )

        return SignalResult(
            symbol=symbol,
            signal=Signal.REJECT,
            score=score,
            reasons=reasons,
            regime=regime_name,
        )
