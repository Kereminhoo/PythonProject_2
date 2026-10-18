from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from data.fundamental_data import (
    FundamentalData,
    FundamentalSnapshot,
)
from data.financial_statement import (
    FinancialPeriod,
    FinancialStatementEngine,
    TTMFinancials,
)
from strategy.fundamental_factors import (
    FundamentalFactorEngine,
    FundamentalFactorResult,
)


# ============================================================
# FUNDAMENTAL CONTEXT
# ============================================================

@dataclass
class FundamentalContext:

    symbol: str

    # Kept as date-only for backward compatibility.
    as_of_date: str

    # Exact point-in-time timestamp when available.
    as_of_datetime: Optional[str]

    snapshot: Optional[
        FundamentalSnapshot
    ]

    current_ttm: Optional[
        TTMFinancials
    ]

    previous_ttm: Optional[
        TTMFinancials
    ]

    factor: Optional[
        FundamentalFactorResult
    ]


# ============================================================
# FUNDAMENTAL CONTEXT ENGINE
# ============================================================

class FundamentalContextEngine:

    def __init__(
        self,
        settings=None,
        fundamental_data: Optional[
            FundamentalData
        ] = None,
        financial_statement_engine: Optional[
            FinancialStatementEngine
        ] = None,
        factor_engine: Optional[
            FundamentalFactorEngine
        ] = None,
    ):

        self.settings = settings

        self.fundamental_data = (
            fundamental_data
            if fundamental_data is not None
            else FundamentalData(
                settings
            )
        )

        self.financial_statement_engine = (
            financial_statement_engine
            if financial_statement_engine is not None
            else FinancialStatementEngine(
                self.fundamental_data
            )
        )

        self.factor_engine = (
            factor_engine
            if factor_engine is not None
            else FundamentalFactorEngine(
                settings
            )
        )

        # ----------------------------------------------------
        # Point-in-time cache.
        #
        # Date-only call:
        #     ("AAPL", "2025-05-15")
        #
        # Intraday call:
        #     ("AAPL", "2025-05-15T14:30:00+00:00")
        #
        # The exact timestamp is required for correctness when
        # a filing becomes available during the trading day.
        # ----------------------------------------------------

        self._context_cache: dict[
            tuple[str, str],
            FundamentalContext,
        ] = {}

    # ========================================================
    # DATE NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_date(
        value: str | date | datetime,
    ) -> str:

        if isinstance(
            value,
            datetime,
        ):

            return value.date().isoformat()

        if isinstance(
            value,
            date,
        ):

            return value.isoformat()

        return str(value)[:10]

    # ========================================================
    # POINT-IN-TIME NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_as_of(
        value: str | date | datetime,
    ) -> tuple[
        Optional[str],
        Optional[datetime],
    ]:

        return (
            FundamentalData
            ._normalize_as_of(
                value
            )
        )

    # ========================================================
    # BUILD TTM
    # ========================================================

    @staticmethod
    def _build_ttm(
            periods: list[FinancialPeriod],
            as_of_date: str,
    ) -> Optional[
        TTMFinancials
    ]:

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Do not blindly use periods[-4:].
        #
        # FinancialStatementEngine validates that these are
        # four genuine and continuous quarterly periods.
        # ----------------------------------------------------

        selected = (
            FinancialStatementEngine
            ._select_ttm_periods(
                periods
            )
        )

        if selected is None:
            return None

        latest = selected[-1]

        previous_quarter = selected[-2]

        # ----------------------------------------------------
        # Additive TTM fields
        # ----------------------------------------------------

        def sum_field(
                field_name: str,
        ) -> Optional[float]:

            values = []

            for period in selected:

                value = getattr(
                    period,
                    field_name,
                    None,
                )

                if value is None:
                    return None

                values.append(
                    float(value)
                )

            return sum(
                values
            )

        revenue_ttm = sum_field(
            "revenue"
        )

        net_income_ttm = sum_field(
            "net_income"
        )

        eps_ttm = sum_field(
            "eps"
        )

        operating_cash_flow_ttm = (
            sum_field(
                "operating_cash_flow"
            )
        )

        capital_expenditure_ttm = (
            sum_field(
                "capital_expenditure"
            )
        )

        free_cash_flow_ttm = sum_field(
            "free_cash_flow"
        )

        # ----------------------------------------------------
        # Use the same sign-aware growth logic as the
        # FinancialStatementEngine.
        # ----------------------------------------------------

        revenue_qoq = (
            FinancialStatementEngine
            ._growth(
                latest.revenue,
                previous_quarter.revenue,
            )
        )

        net_income_qoq = (
            FinancialStatementEngine
            ._growth(
                latest.net_income,
                previous_quarter.net_income,
            )
        )

        eps_qoq = (
            FinancialStatementEngine
            ._growth(
                latest.eps,
                previous_quarter.eps,
            )
        )

        # ----------------------------------------------------
        # Year-ago quarter
        #
        # The fifth-last record is only accepted when it is
        # actually about one year before the latest quarter.
        # ----------------------------------------------------

        year_ago_quarter = None

        if len(periods) >= 5:

            candidate = periods[-5]

            is_year_ago = (
                FinancialStatementEngine
                ._is_year_ago_quarter(
                    latest,
                    candidate,
                )
            )

            if is_year_ago:
                year_ago_quarter = (
                    candidate
                )

        revenue_yoy = None

        net_income_yoy = None

        eps_yoy = None

        fcf_yoy = None

        if (
                year_ago_quarter
                is not None
        ):
            revenue_yoy = (
                FinancialStatementEngine
                ._growth(
                    latest.revenue,
                    year_ago_quarter.revenue,
                )
            )

            net_income_yoy = (
                FinancialStatementEngine
                ._growth(
                    latest.net_income,
                    year_ago_quarter.net_income,
                )
            )

            eps_yoy = (
                FinancialStatementEngine
                ._growth(
                    latest.eps,
                    year_ago_quarter.eps,
                )
            )

            fcf_yoy = (
                FinancialStatementEngine
                ._growth(
                    latest.free_cash_flow,
                    year_ago_quarter.free_cash_flow,
                )
            )

        return TTMFinancials(

            symbol=latest.symbol,

            as_of_date=as_of_date,

            latest_quarter_end=(
                latest.end_date
            ),

            revenue_ttm=revenue_ttm,

            net_income_ttm=(
                net_income_ttm
            ),

            eps_ttm=eps_ttm,

            operating_cash_flow_ttm=(
                operating_cash_flow_ttm
            ),

            capital_expenditure_ttm=(
                capital_expenditure_ttm
            ),

            free_cash_flow_ttm=(
                free_cash_flow_ttm
            ),

            revenue_qoq=revenue_qoq,

            revenue_yoy=revenue_yoy,

            net_income_qoq=(
                net_income_qoq
            ),

            net_income_yoy=(
                net_income_yoy
            ),

            eps_qoq=eps_qoq,

            eps_yoy=eps_yoy,

            fcf_yoy=fcf_yoy,

            latest_filing_accession=(
                latest.filing_accession
            ),

            latest_filing_acceptance_datetime=(
                latest
                .filing_acceptance_datetime
            ),
        )

    # ========================================================
    # BUILD TTM PAIR
    # ========================================================

    def _build_ttm_pair(
        self,
        symbol: str,
        as_of_date: str | date | datetime,
    ) -> tuple[
        Optional[TTMFinancials],
        Optional[TTMFinancials],
    ]:

        (
            normalized_as_of,
            as_of_datetime,
        ) = self._normalize_as_of(
            as_of_date
        )

        # ----------------------------------------------------
        # FinancialStatementEngine now receives the ORIGINAL
        # point-in-time timestamp.
        # ----------------------------------------------------

        periods = (
            self.financial_statement_engine
            .get_quarterly_history(
                symbol=symbol,
                as_of_date=normalized_as_of,
                limit=12,
            )
        )

        if len(periods) < 4:

            return (
                None,
                None,
            )

        current_ttm = (
            self._build_ttm(
                periods=periods,
                as_of_date=(
                    normalized_as_of
                    or ""
                ),
            )
        )

        if current_ttm is None:

            return (
                None,
                None,
            )

        # ----------------------------------------------------
        # Previous TTM
        #
        # [Q-7, Q-6, Q-5, Q-4]
        #
        # Must itself be four continuous quarters.
        # ----------------------------------------------------

        previous_ttm = None

        if len(periods) >= 8:

            previous_periods = periods[
                -8:-4
            ]

            previous_is_continuous = (
                self.financial_statement_engine
                ._is_continuous_ttm_sequence(
                    previous_periods
                )
            )

            if previous_is_continuous:

                previous_ttm = (
                    self._build_ttm(
                        periods=(
                            previous_periods
                        ),
                        as_of_date=(
                            normalized_as_of
                            or ""
                        ),
                    )
                )

        return (
            current_ttm,
            previous_ttm,
        )

    # ========================================================
    # CONTEXT
    # ========================================================

    def get_context(
        self,
        symbol: str,
        as_of_date: str | date | datetime,
    ) -> FundamentalContext:

        symbol = symbol.upper()

        normalized_date = (
            self._normalize_date(
                as_of_date
            )
        )

        (
            normalized_as_of,
            as_of_datetime,
        ) = self._normalize_as_of(
            as_of_date
        )

        # ----------------------------------------------------
        # Exact timestamp is used for cache identity.
        # ----------------------------------------------------

        cache_key = (
            symbol,
            normalized_as_of
            or normalized_date,
        )

        cached = (
            self._context_cache.get(
                cache_key
            )
        )

        if cached is not None:

            return cached

        # ====================================================
        # POINT-IN-TIME SNAPSHOT
        # ====================================================

        snapshot = (
            self.fundamental_data
            .get_snapshot(
                symbol=symbol,
                as_of_date=(
                    normalized_as_of
                    or normalized_date
                ),
            )
        )

        # ====================================================
        # TTM
        # ====================================================

        (
            current_ttm,
            previous_ttm,
        ) = self._build_ttm_pair(
            symbol=symbol,
            as_of_date=(
                normalized_as_of
                or normalized_date
            ),
        )

        # ====================================================
        # FUNDAMENTAL FACTOR
        # ====================================================

        factor = None

        if current_ttm is not None:

            factor = (
                self.factor_engine
                .calculate_from_ttm(
                    current_ttm=current_ttm,
                    previous_ttm=(
                        previous_ttm
                    ),
                    snapshot=snapshot,
                )
            )

        # ====================================================
        # CONTEXT
        # ====================================================

        context = FundamentalContext(

            symbol=symbol,

            as_of_date=normalized_date,

            as_of_datetime=(
                normalized_as_of
                if as_of_datetime is not None
                else None
            ),

            snapshot=snapshot,

            current_ttm=current_ttm,

            previous_ttm=previous_ttm,

            factor=factor,
        )

        # ====================================================
        # CACHE
        # ====================================================

        self._context_cache[
            cache_key
        ] = context

        return context

    # ========================================================
    # CLEAR CACHE
    # ========================================================

    def clear_cache(self) -> None:

        self._context_cache.clear()