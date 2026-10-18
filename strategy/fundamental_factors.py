from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from data.fundamental_data import FundamentalSnapshot
from data.financial_statement import TTMFinancials


# ============================================================
# FUNDAMENTAL FACTOR RESULT
# ============================================================

@dataclass
class FundamentalFactorResult:
    symbol: str

    # --------------------------------------------------------
    # Growth
    # --------------------------------------------------------

    revenue_growth: Optional[float]
    net_income_growth: Optional[float]
    eps_growth: Optional[float]

    # TTM growth
    revenue_ttm_growth: Optional[float]
    net_income_ttm_growth: Optional[float]
    eps_ttm_growth: Optional[float]
    fcf_ttm_growth: Optional[float]

    # --------------------------------------------------------
    # Profitability
    # --------------------------------------------------------

    net_margin: Optional[float]
    roe: Optional[float]

    # --------------------------------------------------------
    # Cash flow
    # --------------------------------------------------------

    free_cash_flow_margin: Optional[float]
    earnings_quality: Optional[float]

    # --------------------------------------------------------
    # Balance sheet
    # --------------------------------------------------------

    debt_to_assets: Optional[float]
    cash_to_assets: Optional[float]

    # --------------------------------------------------------
    # Components
    # --------------------------------------------------------

    growth_score: float
    profitability_score: float
    cash_flow_score: float
    balance_sheet_score: float

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    fundamental_score: float
    data_quality_score: float

    reason: str


# ============================================================
# FUNDAMENTAL FACTOR ENGINE
# ============================================================

class FundamentalFactorEngine:

    # --------------------------------------------------------
    # Component weights
    # --------------------------------------------------------

    GROWTH_WEIGHT = 0.30
    PROFITABILITY_WEIGHT = 0.30
    CASH_FLOW_WEIGHT = 0.20
    BALANCE_SHEET_WEIGHT = 0.20

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        settings=None,
    ):
        self.settings = settings

    # ========================================================
    # SAFE GROWTH
    # ========================================================

    @staticmethod
    def _growth(
            current: Optional[float],
            previous: Optional[float],
    ) -> Optional[float]:

        if current is None:
            return None

        if previous is None:
            return None

        if previous == 0:
            return None

        # Positive -> positive
        if previous > 0 and current >= 0:
            return (current / previous) - 1.0

        # Negative -> negative
        # Example:
        # -200 -> -100 = +50%
        # -100 -> -200 = -100%
        if previous < 0 and current <= 0:
            return (
                    abs(previous) - abs(current)
            ) / abs(previous)

        # Negative -> zero = +100%
        if previous < 0 and current == 0:
            return 1.0

        # Positive -> zero = -100%
        if previous > 0 and current == 0:
            return -1.0

        # Zero crossing:
        # negative -> positive
        # positive -> negative
        return None

    # ========================================================
    # PIECEWISE SCORE
    # ========================================================

    @staticmethod
    def _piecewise_score(
        value: Optional[float],
        thresholds: list[tuple[float, float]],
    ) -> Optional[float]:

        if value is None:
            return None

        if not thresholds:
            return None

        thresholds = sorted(
            thresholds,
            key=lambda item: item[0],
        )

        if value <= thresholds[0][0]:

            return max(
                0.0,
                min(
                    100.0,
                    thresholds[0][1],
                ),
            )

        for index in range(
            1,
            len(thresholds),
        ):

            lower_x, lower_score = (
                thresholds[index - 1]
            )

            upper_x, upper_score = (
                thresholds[index]
            )

            if value <= upper_x:

                distance = (
                    upper_x
                    - lower_x
                )

                if distance == 0:
                    return upper_score

                fraction = (
                    value - lower_x
                ) / distance

                score = (
                    lower_score
                    + fraction
                    * (
                        upper_score
                        - lower_score
                    )
                )

                return max(
                    0.0,
                    min(
                        100.0,
                        score,
                    ),
                )

        return max(
            0.0,
            min(
                100.0,
                thresholds[-1][1],
            ),
        )

    # ========================================================
    # GROWTH SCORE
    # ========================================================

    @classmethod
    def score_growth(
        cls,
        growth: Optional[float],
    ) -> Optional[float]:

        return cls._piecewise_score(
            growth,
            [
                (-0.30, 0),
                (-0.20, 15),
                (-0.10, 30),
                (0.00, 50),
                (0.05, 60),
                (0.10, 70),
                (0.20, 85),
                (0.30, 95),
                (0.40, 100),
            ],
        )

    # ========================================================
    # MARGIN SCORE
    # ========================================================

    @classmethod
    def score_margin(
        cls,
        margin: Optional[float],
    ) -> Optional[float]:

        return cls._piecewise_score(
            margin,
            [
                (-0.10, 0),
                (0.00, 30),
                (0.05, 45),
                (0.10, 60),
                (0.15, 70),
                (0.20, 82),
                (0.25, 92),
                (0.30, 100),
            ],
        )

    # ========================================================
    # ROE SCORE
    # ========================================================

    @classmethod
    def score_roe(
        cls,
        roe: Optional[float],
    ) -> Optional[float]:

        return cls._piecewise_score(
            roe,
            [
                (-0.10, 0),
                (0.00, 25),
                (0.05, 40),
                (0.10, 60),
                (0.15, 75),
                (0.20, 90),
                (0.25, 100),
            ],
        )

    # ========================================================
    # FCF MARGIN
    # ========================================================

    @classmethod
    def score_fcf_margin(
        cls,
        margin: Optional[float],
    ) -> Optional[float]:

        return cls._piecewise_score(
            margin,
            [
                (-0.10, 0),
                (0.00, 25),
                (0.05, 45),
                (0.10, 65),
                (0.15, 80),
                (0.20, 92),
                (0.25, 100),
            ],
        )

    # ========================================================
    # EARNINGS QUALITY
    # ========================================================

    @classmethod
    def score_earnings_quality(
        cls,
        quality: Optional[float],
    ) -> Optional[float]:

        return cls._piecewise_score(
            quality,
            [
                (-1.00, 0),
                (0.00, 20),
                (0.50, 50),
                (0.75, 70),
                (1.00, 85),
                (1.25, 95),
                (1.50, 100),
            ],
        )

    # ========================================================
    # DEBT SCORE
    # ========================================================

    @classmethod
    def score_debt(
        cls,
        debt_to_assets: Optional[float],
    ) -> Optional[float]:

        if debt_to_assets is None:
            return None

        return cls._piecewise_score(
            debt_to_assets,
            [
                (0.20, 100),
                (0.30, 90),
                (0.40, 75),
                (0.50, 60),
                (0.60, 45),
                (0.75, 25),
                (0.90, 10),
                (1.00, 0),
            ],
        )

    # ========================================================
    # CASH SCORE
    # ========================================================

    @classmethod
    def score_cash(
        cls,
        cash_to_assets: Optional[float],
    ) -> Optional[float]:

        return cls._piecewise_score(
            cash_to_assets,
            [
                (0.00, 20),
                (0.05, 40),
                (0.10, 60),
                (0.15, 80),
                (0.20, 95),
                (0.25, 100),
            ],
        )

    # ========================================================
    # AVERAGE SCORES
    # ========================================================

    @staticmethod
    def _average_scores(
        scores: list[Optional[float]],
    ) -> float:

        available = [
            score
            for score in scores
            if score is not None
        ]

        if not available:
            return 0.0

        return (
            sum(available)
            / len(available)
        )

    # ========================================================
    # EARNINGS QUALITY FROM TTM
    # ========================================================

    @staticmethod
    def _ttm_earnings_quality(
        ttm: Optional[TTMFinancials],
    ) -> Optional[float]:

        if ttm is None:
            return None

        if (
            ttm.free_cash_flow_ttm is None
            or ttm.net_income_ttm is None
        ):
            return None

        if ttm.net_income_ttm == 0:
            return None

        return (
            ttm.free_cash_flow_ttm
            / ttm.net_income_ttm
        )

    # ========================================================
    # TTM FCF MARGIN
    # ========================================================

    @staticmethod
    def _ttm_fcf_margin(
        ttm: Optional[TTMFinancials],
    ) -> Optional[float]:

        if ttm is None:
            return None

        if (
            ttm.free_cash_flow_ttm is None
            or ttm.revenue_ttm is None
        ):
            return None

        if ttm.revenue_ttm == 0:
            return None

        return (
            ttm.free_cash_flow_ttm
            / ttm.revenue_ttm
        )

    # ========================================================
    # CURRENT / PREVIOUS TTM GROWTH
    # ========================================================

    @staticmethod
    def _ttm_growth(
            current_value: Optional[float],
            previous_value: Optional[float],
    ) -> Optional[float]:

        return FundamentalFactorEngine._growth(
            current_value,
            previous_value,
        )

    # ========================================================
    # TTM COMPONENT CALCULATION
    # ========================================================

    def calculate_from_ttm(
        self,
        current_ttm: TTMFinancials,
        previous_ttm: Optional[TTMFinancials],
        snapshot: Optional[FundamentalSnapshot] = None,
    ) -> FundamentalFactorResult:
        """
        TTM-aware fundamental calculation.

        TTM growth is calculated against the previous TTM period.
        Profitability / balance-sheet fields come from the
        point-in-time FundamentalSnapshot.

        This method is deliberately separate from calculate()
        so existing callers remain backward compatible.
        """

        # ----------------------------------------------------
        # TTM growth
        # ----------------------------------------------------

        revenue_ttm_growth = None
        net_income_ttm_growth = None
        eps_ttm_growth = None
        fcf_ttm_growth = None

        if previous_ttm is not None:

            revenue_ttm_growth = (
                self._ttm_growth(
                    current_ttm.revenue_ttm,
                    previous_ttm.revenue_ttm,
                )
            )

            net_income_ttm_growth = (
                self._ttm_growth(
                    current_ttm.net_income_ttm,
                    previous_ttm.net_income_ttm,
                )
            )

            eps_ttm_growth = (
                self._ttm_growth(
                    current_ttm.eps_ttm,
                    previous_ttm.eps_ttm,
                )
            )

            fcf_ttm_growth = (
                self._ttm_growth(
                    current_ttm.free_cash_flow_ttm,
                    previous_ttm.free_cash_flow_ttm,
                )
            )

        # ----------------------------------------------------
        # Also preserve latest quarter growth information.
        # ----------------------------------------------------

        revenue_growth = (
            current_ttm.revenue_qoq
        )

        net_income_growth = (
            current_ttm.net_income_qoq
        )

        eps_growth = (
            current_ttm.eps_qoq
        )

        # ----------------------------------------------------
        # Profitability / balance sheet
        # ----------------------------------------------------

        net_margin = (
            snapshot.net_margin
            if snapshot is not None
            else None
        )

        roe = (
            snapshot.return_on_equity
            if snapshot is not None
            else None
        )

        debt_to_assets = (
            snapshot.debt_to_assets
            if snapshot is not None
            else None
        )

        cash_to_assets = (
            snapshot.cash_to_assets
            if snapshot is not None
            else None
        )

        # ----------------------------------------------------
        # TTM cash flow
        # ----------------------------------------------------

        fcf_margin = (
            self._ttm_fcf_margin(
                current_ttm
            )
        )

        earnings_quality = (
            self._ttm_earnings_quality(
                current_ttm
            )
        )

        # ----------------------------------------------------
        # Growth score
        # ----------------------------------------------------
        #
        # TTM growth gets the highest importance because it
        # compares the current trailing business with the prior
        # trailing period and is less sensitive to single-quarter
        # noise.
        #

        revenue_ttm_score = (
            self.score_growth(
                revenue_ttm_growth
            )
        )

        net_income_ttm_score = (
            self.score_growth(
                net_income_ttm_growth
            )
        )

        eps_ttm_score = (
            self.score_growth(
                eps_ttm_growth
            )
        )

        # QoQ contributes as a secondary signal.
        revenue_qoq_score = (
            self.score_growth(
                revenue_growth
            )
        )

        growth_score = self._average_scores(
            [
                revenue_ttm_score,
                net_income_ttm_score,
                eps_ttm_score,
                revenue_qoq_score,
            ]
        )

        # ----------------------------------------------------
        # Profitability
        # ----------------------------------------------------

        profitability_score = (
            self._average_scores(
                [
                    self.score_margin(
                        net_margin
                    ),
                    self.score_roe(
                        roe
                    ),
                ]
            )
        )

        # ----------------------------------------------------
        # Cash Flow
        # ----------------------------------------------------

        cash_flow_score = (
            self._average_scores(
                [
                    self.score_fcf_margin(
                        fcf_margin
                    ),
                    self.score_earnings_quality(
                        earnings_quality
                    ),
                    self.score_growth(
                        fcf_ttm_growth
                    ),
                ]
            )
        )

        # ----------------------------------------------------
        # Balance Sheet
        # ----------------------------------------------------

        balance_sheet_score = (
            self._average_scores(
                [
                    self.score_debt(
                        debt_to_assets
                    ),
                    self.score_cash(
                        cash_to_assets
                    ),
                ]
            )
        )

        # ----------------------------------------------------
        # Weighted score
        # ----------------------------------------------------

        fundamental_score = (
            growth_score
            * self.GROWTH_WEIGHT

            +

            profitability_score
            * self.PROFITABILITY_WEIGHT

            +

            cash_flow_score
            * self.CASH_FLOW_WEIGHT

            +

            balance_sheet_score
            * self.BALANCE_SHEET_WEIGHT
        )

        fundamental_score = max(
            0.0,
            min(
                100.0,
                fundamental_score,
            ),
        )

        # ----------------------------------------------------
        # Data quality
        # ----------------------------------------------------

        fields = [
            current_ttm.revenue_ttm,
            current_ttm.net_income_ttm,
            current_ttm.eps_ttm,
            current_ttm.free_cash_flow_ttm,
            revenue_ttm_growth,
            net_income_ttm_growth,
            eps_ttm_growth,
            fcf_ttm_growth,
            net_margin,
            roe,
            debt_to_assets,
            cash_to_assets,
        ]

        available_fields = sum(
            value is not None
            for value in fields
        )

        data_quality_score = (
            available_fields
            / len(fields)
            * 100.0
        )

        # ----------------------------------------------------
        # Explanation
        # ----------------------------------------------------

        reasons = []

        if growth_score >= 75:

            reasons.append(
                "strong TTM growth"
            )

        elif growth_score < 40:

            reasons.append(
                "weak TTM growth"
            )

        if profitability_score >= 75:

            reasons.append(
                "strong profitability"
            )

        elif profitability_score < 40:

            reasons.append(
                "weak profitability"
            )

        if cash_flow_score >= 75:

            reasons.append(
                "strong cash flow"
            )

        elif cash_flow_score < 40:

            reasons.append(
                "weak cash flow"
            )

        if balance_sheet_score >= 75:

            reasons.append(
                "healthy balance sheet"
            )

        elif balance_sheet_score < 40:

            reasons.append(
                "weak balance sheet"
            )

        reason = (
            "; ".join(reasons)
            if reasons
            else "insufficient fundamental differentiation"
        )

        return FundamentalFactorResult(

            symbol=current_ttm.symbol,

            revenue_growth=revenue_growth,

            net_income_growth=net_income_growth,

            eps_growth=eps_growth,

            revenue_ttm_growth=(
                revenue_ttm_growth
            ),

            net_income_ttm_growth=(
                net_income_ttm_growth
            ),

            eps_ttm_growth=(
                eps_ttm_growth
            ),

            fcf_ttm_growth=(
                fcf_ttm_growth
            ),

            net_margin=net_margin,

            roe=roe,

            free_cash_flow_margin=(
                fcf_margin
            ),

            earnings_quality=(
                earnings_quality
            ),

            debt_to_assets=(
                debt_to_assets
            ),

            cash_to_assets=(
                cash_to_assets
            ),

            growth_score=growth_score,

            profitability_score=(
                profitability_score
            ),

            cash_flow_score=(
                cash_flow_score
            ),

            balance_sheet_score=(
                balance_sheet_score
            ),

            fundamental_score=(
                fundamental_score
            ),

            data_quality_score=(
                data_quality_score
            ),

            reason=reason,
        )

    # ========================================================
    # LEGACY / SNAPSHOT CALCULATION
    # ========================================================

    def calculate(
        self,
        current: FundamentalSnapshot,
        previous: Optional[FundamentalSnapshot] = None,
    ) -> FundamentalFactorResult:

        # ----------------------------------------------------
        # Existing snapshot growth
        # ----------------------------------------------------

        revenue_growth = None
        net_income_growth = None
        eps_growth = None

        if previous is not None:

            revenue_growth = self._growth(
                current.revenue,
                previous.revenue,
            )

            net_income_growth = self._growth(
                current.net_income,
                previous.net_income,
            )

            eps_growth = self._growth(
                current.eps,
                previous.eps,
            )

        # ----------------------------------------------------
        # Earnings quality
        # ----------------------------------------------------

        earnings_quality = None

        if (
            current.free_cash_flow is not None
            and current.net_income is not None
            and current.net_income != 0
        ):

            earnings_quality = (
                current.free_cash_flow
                / current.net_income
            )

        # ----------------------------------------------------
        # Scores
        # ----------------------------------------------------

        revenue_growth_score = (
            self.score_growth(
                revenue_growth
            )
        )

        net_income_growth_score = (
            self.score_growth(
                net_income_growth
            )
        )

        eps_growth_score = (
            self.score_growth(
                eps_growth
            )
        )

        net_margin_score = (
            self.score_margin(
                current.net_margin
            )
        )

        roe_score = (
            self.score_roe(
                current.return_on_equity
            )
        )

        fcf_margin_score = (
            self.score_fcf_margin(
                current.free_cash_flow_margin
            )
        )

        earnings_quality_score = (
            self.score_earnings_quality(
                earnings_quality
            )
        )

        debt_score = (
            self.score_debt(
                current.debt_to_assets
            )
        )

        cash_score = (
            self.score_cash(
                current.cash_to_assets
            )
        )

        # ----------------------------------------------------
        # Components
        # ----------------------------------------------------

        growth_score = self._average_scores(
            [
                revenue_growth_score,
                net_income_growth_score,
                eps_growth_score,
            ]
        )

        profitability_score = (
            self._average_scores(
                [
                    net_margin_score,
                    roe_score,
                ]
            )
        )

        cash_flow_score = (
            self._average_scores(
                [
                    fcf_margin_score,
                    earnings_quality_score,
                ]
            )
        )

        balance_sheet_score = (
            self._average_scores(
                [
                    debt_score,
                    cash_score,
                ]
            )
        )

        # ----------------------------------------------------
        # Final
        # ----------------------------------------------------

        fundamental_score = (
            growth_score
            * self.GROWTH_WEIGHT
            +
            profitability_score
            * self.PROFITABILITY_WEIGHT
            +
            cash_flow_score
            * self.CASH_FLOW_WEIGHT
            +
            balance_sheet_score
            * self.BALANCE_SHEET_WEIGHT
        )

        fundamental_score = max(
            0.0,
            min(
                100.0,
                fundamental_score,
            ),
        )

        # ----------------------------------------------------
        # Data quality
        # ----------------------------------------------------

        fields = [
            current.revenue,
            current.net_income,
            current.eps,
            current.net_margin,
            current.return_on_equity,
            current.free_cash_flow_margin,
            earnings_quality,
            current.debt_to_assets,
            current.cash_to_assets,
        ]

        available_fields = sum(
            field is not None
            for field in fields
        )

        data_quality_score = (
            available_fields
            / len(fields)
            * 100.0
        )

        # ----------------------------------------------------
        # Reason
        # ----------------------------------------------------

        reasons = []

        if growth_score >= 75:

            reasons.append(
                "strong growth"
            )

        elif growth_score < 40:

            reasons.append(
                "weak growth"
            )

        if profitability_score >= 75:

            reasons.append(
                "strong profitability"
            )

        elif profitability_score < 40:

            reasons.append(
                "weak profitability"
            )

        if cash_flow_score >= 75:

            reasons.append(
                "strong cash flow"
            )

        elif cash_flow_score < 40:

            reasons.append(
                "weak cash flow"
            )

        if balance_sheet_score >= 75:

            reasons.append(
                "healthy balance sheet"
            )

        elif balance_sheet_score < 40:

            reasons.append(
                "weak balance sheet"
            )

        reason = (
            "; ".join(reasons)
            if reasons
            else "insufficient fundamental differentiation"
        )

        return FundamentalFactorResult(

            symbol=current.symbol,

            revenue_growth=revenue_growth,

            net_income_growth=(
                net_income_growth
            ),

            eps_growth=eps_growth,

            revenue_ttm_growth=None,

            net_income_ttm_growth=None,

            eps_ttm_growth=None,

            fcf_ttm_growth=None,

            net_margin=current.net_margin,

            roe=current.return_on_equity,

            free_cash_flow_margin=(
                current.free_cash_flow_margin
            ),

            earnings_quality=(
                earnings_quality
            ),

            debt_to_assets=(
                current.debt_to_assets
            ),

            cash_to_assets=(
                current.cash_to_assets
            ),

            growth_score=growth_score,

            profitability_score=(
                profitability_score
            ),

            cash_flow_score=(
                cash_flow_score
            ),

            balance_sheet_score=(
                balance_sheet_score
            ),

            fundamental_score=(
                fundamental_score
            ),

            data_quality_score=(
                data_quality_score
            ),

            reason=reason,
        )