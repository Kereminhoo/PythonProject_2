import pytest

from data.financial_statement import (
    FinancialPeriod,
)

from data.fundamental_context import (
    FundamentalContextEngine,
)


def make_period(
    quarter,
    revenue,
    net_income,
    eps,
    fcf,
    year=2025,
    filed_date="2025-05-01",
):
    months = {
        "Q1": ("01-01", "03-31"),
        "Q2": ("04-01", "06-30"),
        "Q3": ("07-01", "09-30"),
        "Q4": ("10-01", "12-31"),
    }

    start, end = months[quarter]

    return FinancialPeriod(

        symbol="AAPL",

        start_date=f"{year}-{start}",

        end_date=f"{year}-{end}",

        filed_date=filed_date,

        form=(
            "10-K"
            if quarter == "Q4"
            else "10-Q"
        ),

        fiscal_year=year,

        fiscal_period=quarter,

        revenue=revenue,

        net_income=net_income,

        eps=eps,

        operating_cash_flow=(
            fcf + 50
        ),

        capital_expenditure=50,

        free_cash_flow=fcf,
    )


# ============================================================
# FAKE ENGINE
# ============================================================


class FakeFinancialStatementEngine:

    def __init__(self):

        self.periods = [

            make_period(
                "Q1",
                100,
                10,
                1.0,
                10,
            ),

            make_period(
                "Q2",
                110,
                12,
                1.1,
                11,
            ),

            make_period(
                "Q3",
                120,
                14,
                1.2,
                12,
            ),

            make_period(
                "Q4",
                130,
                16,
                1.3,
                13,
            ),
        ]

    def get_quarterly_history(
        self,
        symbol,
        as_of_date=None,
        limit=12,
    ):

        return self.periods[-limit:]

    @staticmethod
    def _select_ttm_periods(
        periods,
    ):

        if len(periods) < 4:
            return None

        return periods[-4:]

    @staticmethod
    def _growth(
        current,
        previous,
    ):

        if current is None:
            return None

        if previous is None:
            return None

        if previous == 0:
            return None

        if (
            previous < 0
            and current <= 0
        ):

            return (
                abs(previous)
                - abs(current)
            ) / abs(previous)

        if (
            previous > 0
            and current >= 0
        ):

            return (
                current / previous
            ) - 1.0

        if (
            previous < 0
            and current == 0
        ):

            return 1.0

        if (
            previous > 0
            and current == 0
        ):

            return -1.0

        return None

    @staticmethod
    def _is_year_ago_quarter(
        latest,
        year_ago,
    ):

        latest_end = latest.end_date
        year_ago_end = year_ago.end_date

        return (
            latest_end[:4]
            != year_ago_end[:4]
        )


# ============================================================
# DATE
# ============================================================


def test_normalize_date():

    engine = FundamentalContextEngine()

    result = engine._normalize_date(
        "2025-05-15T12:00:00"
    )

    assert result == "2025-05-15"


def test_normalize_as_of_preserves_datetime():

    engine = FundamentalContextEngine()

    normalized, as_of_datetime = (
        engine._normalize_as_of(
            "2025-05-15T12:00:00Z"
        )
    )

    assert (
        normalized
        == "2025-05-15T12:00:00+00:00"
    )

    assert as_of_datetime is not None

    assert as_of_datetime.hour == 12

    assert as_of_datetime.minute == 0


# ============================================================
# TTM
# ============================================================


def test_build_ttm():

    engine = FundamentalContextEngine()

    periods = [

        make_period(
            "Q1",
            100,
            10,
            1.0,
            10,
        ),

        make_period(
            "Q2",
            110,
            12,
            1.1,
            11,
        ),

        make_period(
            "Q3",
            120,
            14,
            1.2,
            12,
        ),

        make_period(
            "Q4",
            130,
            16,
            1.3,
            13,
        ),
    ]

    result = engine._build_ttm(
        periods,
        "2025-12-31",
    )

    assert result is not None

    assert result.revenue_ttm == 460

    assert result.net_income_ttm == 52

    assert (
        result.free_cash_flow_ttm
        == 46
    )


def test_ttm_growth():

    engine = FundamentalContextEngine()

    current = engine._build_ttm(
        [

            make_period(
                "Q1",
                100,
                10,
                1.0,
                10,
            ),

            make_period(
                "Q2",
                110,
                12,
                1.1,
                11,
            ),

            make_period(
                "Q3",
                120,
                14,
                1.2,
                12,
            ),

            make_period(
                "Q4",
                130,
                16,
                1.3,
                13,
            ),
        ],
        "2025-12-31",
    )

    assert current is not None

    assert (
        current.revenue_ttm
        == 460
    )

    assert (
        current.revenue_qoq
        == pytest.approx(
            130 / 120 - 1
        )
    )


def test_ttm_rejects_non_continuous_periods():

    engine = FundamentalContextEngine()

    periods = [

        make_period(
            "Q1",
            100,
            10,
            1.0,
            10,
        ),

        # Q2 missing.

        make_period(
            "Q3",
            120,
            14,
            1.2,
            12,
        ),

        make_period(
            "Q4",
            130,
            16,
            1.3,
            13,
        ),

        make_period(
            "Q1",
            140,
            18,
            1.4,
            14,
            year=2026,
        ),
    ]

    result = engine._build_ttm(
        periods,
        "2026-03-31",
    )

    assert result is None


def test_ttm_uses_sign_aware_growth():

    engine = FundamentalContextEngine()

    periods = [

        make_period(
            "Q1",
            -200,
            -20,
            -2.0,
            10,
        ),

        make_period(
            "Q2",
            -180,
            -18,
            -1.8,
            11,
        ),

        make_period(
            "Q3",
            -150,
            -15,
            -1.5,
            12,
        ),

        make_period(
            "Q4",
            -100,
            -10,
            -1.0,
            13,
        ),
    ]

    result = engine._build_ttm(
        periods,
        "2025-12-31",
    )

    assert result is not None

    assert (
        result.revenue_qoq
        == pytest.approx(
            1 / 3
        )
    )


# ============================================================
# TTM PAIR
# ============================================================


def test_ttm_pair_requires_eight_periods():

    engine = FundamentalContextEngine(
        financial_statement_engine=(
            FakeFinancialStatementEngine()
        )
    )

    current, previous = (
        engine._build_ttm_pair(
            "AAPL",
            "2025-12-31",
        )
    )

    assert current is not None

    assert previous is None


def test_ttm_pair_with_eight_periods():

    engine = FundamentalContextEngine()

    periods = []

    for year, filed_date in [
        (2024, "2025-05-01"),
        (2025, "2026-05-01"),
    ]:

        values = [

            (
                "Q1",
                (100, 10, 1.0, 10),
            ),

            (
                "Q2",
                (110, 12, 1.1, 11),
            ),

            (
                "Q3",
                (120, 14, 1.2, 12),
            ),

            (
                "Q4",
                (130, 16, 1.3, 13),
            ),
        ]

        for quarter, data in values:

            revenue, net_income, eps, fcf = (
                data
            )

            periods.append(
                make_period(
                    quarter=quarter,
                    revenue=revenue,
                    net_income=net_income,
                    eps=eps,
                    fcf=fcf,
                    year=year,
                    filed_date=filed_date,
                )
            )

    class EightPeriodEngine:

        def get_quarterly_history(
            self,
            symbol,
            as_of_date=None,
            limit=12,
        ):

            return periods

        def _select_ttm_periods(
            self,
            values,
        ):

            if len(values) < 4:
                return None

            return values[-4:]

        def _is_continuous_ttm_sequence(
            self,
            values,
        ):

            return True

        def _is_year_ago_quarter(
            self,
            latest,
            year_ago,
        ):

            return True

        def _growth(
            self,
            current,
            previous,
        ):

            if current is None:
                return None

            if previous is None:
                return None

            if previous == 0:
                return None

            if (
                previous < 0
                and current <= 0
            ):

                return (
                    abs(previous)
                    - abs(current)
                ) / abs(previous)

            if (
                previous > 0
                and current >= 0
            ):

                return (
                    current / previous
                ) - 1

            return None

    engine = FundamentalContextEngine(
        financial_statement_engine=(
            EightPeriodEngine()
        )
    )

    current, previous = (
        engine._build_ttm_pair(
            "AAPL",
            "2026-06-01",
        )
    )

    assert current is not None

    assert previous is not None

    assert (
        current.revenue_ttm
        == 460
    )

    assert (
        previous.revenue_ttm
        == 460
    )


# ============================================================
# CACHE
# ============================================================


def test_cache_returns_same_object():

    engine = FundamentalContextEngine()

    context = engine.get_context(
        "UNKNOWN_SYMBOL",
        "2025-01-15",
    )

    context_again = engine.get_context(
        "UNKNOWN_SYMBOL",
        "2025-01-15",
    )

    assert context is context_again


def test_different_dates_use_different_cache_entries():

    engine = FundamentalContextEngine()

    first = engine.get_context(
        "UNKNOWN_SYMBOL",
        "2025-01-15",
    )

    second = engine.get_context(
        "UNKNOWN_SYMBOL",
        "2025-01-16",
    )

    assert first is not second


def test_intraday_cache_entries_are_different():

    engine = FundamentalContextEngine()

    first = engine.get_context(
        "UNKNOWN_SYMBOL",
        "2025-01-15T10:00:00Z",
    )

    second = engine.get_context(
        "UNKNOWN_SYMBOL",
        "2025-01-15T15:00:00Z",
    )

    assert first is not second