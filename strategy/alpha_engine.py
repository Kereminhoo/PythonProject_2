from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ============================================================
# COMBINED ALPHA RESULT
# ============================================================

@dataclass
class AlphaResult:
    symbol: str

    technical_score: float
    fundamental_score: Optional[float]

    regime: str

    base_score: float
    regime_adjustment: float
    final_score: float

    technical_weight: float
    fundamental_weight: float

    data_quality_score: Optional[float]

    fundamental_available: bool
    alpha_mode: str

    eligible: bool
    reason: str


# ============================================================
# COMBINED ALPHA ENGINE (SWING TRADING REVISION)
# ============================================================

class CombinedAlphaEngine:
    """
    Combines:

        Technical Alpha
        Fundamental Alpha
        Market Regime

    into a single 0-100 alpha score.

    Architecture:

        Technical
             +
        Fundamental
             +
        ONE Regime Adjustment
             =
        Final Alpha

    Important:
        Market regime must NOT be added to the technical
        SignalEngine score.

        Regime adjustment is applied exactly once here.
    """

    # For Swing Trading, Technicals drive the decision. Fundamentals are just a bonus.
    DEFAULT_TECHNICAL_WEIGHT = 0.85 
    DEFAULT_FUNDAMENTAL_WEIGHT = 0.15

    REGIME_ADJUSTMENTS = {
        "BULL": 10.0,      # Boosted for Swing Trading
        "SIDEWAYS": 0.0,
        "HIGH_VOLATILITY": -5.0,
        "BEAR": -15.0,
        "UNKNOWN": 0.0,
    }

    ALPHA_MODE_MULTI_FACTOR = "MULTI_FACTOR"
    ALPHA_MODE_TECHNICAL_FALLBACK = "TECHNICAL_FALLBACK"

    def __init__(
        self,
        technical_weight: float = DEFAULT_TECHNICAL_WEIGHT,
        fundamental_weight: float = DEFAULT_FUNDAMENTAL_WEIGHT,
        # Lowered significantly. We don't want to miss a great technical setup just because a company missed one balance sheet metric.
        minimum_data_quality: float = 20.0, 
    ):

        if (
            technical_weight < 0
            or fundamental_weight < 0
        ):
            raise ValueError(
                "Alpha weights cannot be negative."
            )

        total_weight = (
            technical_weight
            + fundamental_weight
        )

        if total_weight <= 0:

            raise ValueError(
                "Alpha weights must sum to a positive value."
            )

        self.technical_weight = (
            technical_weight
            / total_weight
        )

        self.fundamental_weight = (
            fundamental_weight
            / total_weight
        )

        self.minimum_data_quality = (
            float(minimum_data_quality)
        )

    # ========================================================
    # CLAMP
    # ========================================================

    @staticmethod
    def _clamp_score(
        value: float,
    ) -> float:

        return max(
            0.0,
            min(
                100.0,
                float(value),
            ),
        )

    # ========================================================
    # NORMALIZE REGIME
    # ========================================================

    @staticmethod
    def _normalize_regime(
        regime,
    ) -> str:

        if regime is None:

            return "UNKNOWN"

        if hasattr(
            regime,
            "value",
        ):

            value = regime.value

            if hasattr(
                value,
                "value",
            ):
                value = value.value

            return str(
                value
            ).upper()

        if hasattr(
            regime,
            "regime",
        ):

            nested_regime = (
                regime.regime
            )

            if hasattr(
                nested_regime,
                "value",
            ):

                return str(
                    nested_regime.value
                ).upper()

            return str(
                nested_regime
            ).upper()

        normalized = str(
            regime
        ).upper()

        if "." in normalized:

            normalized = (
                normalized
                .split(".")[-1]
            )

        return normalized

    # ========================================================
    # CALCULATE
    # ========================================================

    def calculate(
        self,
        symbol: str,
        technical_score: float,
        fundamental_score: Optional[float],
        regime="UNKNOWN",
        data_quality_score: Optional[float] = None,
    ) -> AlphaResult:

        # ====================================================
        # NORMALIZE INPUTS
        # ====================================================

        technical_score = (
            self._clamp_score(
                technical_score
            )
        )

        normalized_regime = (
            self._normalize_regime(
                regime
            )
        )

        regime_adjustment = (
            self.REGIME_ADJUSTMENTS.get(
                normalized_regime,
                0.0,
            )
        )

        # ====================================================
        # FUNDAMENTAL AVAILABILITY
        # ====================================================

        fundamental_available = (
            fundamental_score is not None
        )

        if fundamental_available:

            fundamental_score = (
                self._clamp_score(
                    fundamental_score
                )
            )

        # ====================================================
        # DATA QUALITY (RELAXED FOR SWING)
        # ====================================================

        quality_ok = True

        if fundamental_available:

            if data_quality_score is None:

                quality_ok = False

            else:

                quality_ok = (
                    float(data_quality_score)
                    >= self.minimum_data_quality
                )

        # ====================================================
        # ALPHA MODE
        # ====================================================

        if fundamental_available:

            alpha_mode = (
                self.ALPHA_MODE_MULTI_FACTOR
            )

        else:

            alpha_mode = (
                self.ALPHA_MODE_TECHNICAL_FALLBACK
            )

        # ====================================================
        # BASE SCORE (TECH HEAVY)
        # ====================================================

        if fundamental_available and quality_ok:

            base_score = (
                technical_score
                * self.technical_weight
                +
                fundamental_score
                * self.fundamental_weight
            )

        else:

            # Even if fundamentals are available but data quality is low,
            # we don't reject the trade anymore. We just fall back to 100% Technical.
            base_score = technical_score
            alpha_mode = self.ALPHA_MODE_TECHNICAL_FALLBACK
            fundamental_available = False # Treat as fallback

        # ====================================================
        # FINAL SCORE
        # ====================================================

        final_score = self._clamp_score(
            base_score
            + regime_adjustment
        )

        # ====================================================
        # ELIGIBILITY (NEVER REJECT A GOOD TECHNICAL SETUP)
        # ====================================================
        
        # In Swing Trading, if the technical trend is strong, we trade it.
        # We no longer reject trades solely because of bad fundamental data quality.
        eligible = True 

        # ====================================================
        # EXPLANATION
        # ====================================================

        reasons = []

        if alpha_mode == (
            self.ALPHA_MODE_MULTI_FACTOR
        ):

            reasons.append(
                "multi-factor alpha"
            )

            if fundamental_score is not None:

                if fundamental_score >= 75:

                    reasons.append(
                        "strong fundamentals"
                    )

                elif fundamental_score < 40:

                    reasons.append(
                        "weak fundamentals"
                    )

        else:

            reasons.append(
                "technical fallback"
            )

            if not quality_ok:
                 reasons.append(
                    "fundamental data quality too low, using pure technicals"
                )
            else:
                reasons.append(
                    "fundamental data unavailable"
                )

        # ----------------------------------------------------
        # Regime
        # ----------------------------------------------------

        if normalized_regime == "BULL":

            reasons.append(
                "bull regime"
            )

        elif normalized_regime == "BEAR":

            reasons.append(
                "bear regime"
            )

        elif normalized_regime == "HIGH_VOLATILITY":

            reasons.append(
                "high volatility"
            )

        elif normalized_regime == "SIDEWAYS":

            reasons.append(
                "sideways regime"
            )


        # ----------------------------------------------------
        # Eligibility
        # ----------------------------------------------------

        if eligible:

            reasons.append(
                "eligible"
            )

        else:

            reasons.append(
                "ineligible"
            )

        # ====================================================
        # RESULT
        # ====================================================

        return AlphaResult(

            symbol=symbol,

            technical_score=technical_score,

            fundamental_score=fundamental_score,

            regime=normalized_regime,

            base_score=base_score,

            regime_adjustment=regime_adjustment,

            final_score=final_score,

            technical_weight=(
                self.technical_weight
            ),

            fundamental_weight=(
                self.fundamental_weight
            ),

            data_quality_score=(
                data_quality_score
            ),

            fundamental_available=(
                fundamental_available
            ),

            alpha_mode=(
                alpha_mode
            ),

            eligible=eligible,

            reason="; ".join(reasons),
        )