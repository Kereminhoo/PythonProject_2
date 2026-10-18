from __future__ import annotations

from datetime import date, timedelta

from data.financial_statement import (
    FinancialPeriod,
    FinancialStatementEngine,
)
from data.fundamental_context import (
    FundamentalContextEngine,
)


# ============================================================
# FAKE FUNDAMENTAL DATA
# ============================================================

class FakeFundamentalData:

    def __init__(self, facts):
        self.facts = facts

    def get_company_facts(self, symbol):
        return self.facts


# ============================================================
# HELPERS
# ============================================================

def build_quarter_entry(
    start: date,
    end: date,
    filed: date,
    value: float,
    fiscal_year: int,
    fiscal_period: str,
) -> dict:

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "filed": filed.isoformat(),
        "form": "10-Q",
        "fy": fiscal_year,
        "fp": fiscal_period,
        "val": value,
    }


def build_revenue_facts():

    entries = []

    first_start = date(2023, 1, 1)

    values = [
        100.0,
        110.0,
        120.0,
        130.0,
        140.0,
        150.0,
        160.0,
        200.0,
    ]

    fiscal_periods = [
        (2023, "Q1"),
        (2023, "Q2"),
        (2023, "Q3"),
        (2023, "Q4"),
        (2024, "Q1"),
        (2024, "Q2"),
        (2024, "Q3"),
        (2024, "Q4"),
    ]

    for index, (
        value,
        fiscal_info,
    ) in enumerate(
        zip(
            values,
            fiscal_periods,
        )
    ):

        start = (
            first_start
            + timedelta(days=index * 90)
        )

        end = (
            start
            + timedelta(days=89)
        )

        filed = (
            end
            + timedelta(days=30)
        )

        fiscal_year, fiscal_period = (
            fiscal_info
        )

        entries.append(
            build_quarter_entry(
                start=start,
                end=end,
                filed=filed,
                value=value,
                fiscal_year=fiscal_year,
                fiscal_period=fiscal_period,
            )
        )

    return {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": entries
                    }
                }
            }
        }
    }


# ============================================================
# TEST: FINANCIAL PERIOD ORDER
# ============================================================

def test_quarterly_history_is_chronological():

    facts = build_revenue_facts()

    fake_data = FakeFundamentalData(
        facts
    )

    engine = FinancialStatementEngine(
        fake_data
    )

    periods = engine.get_quarterly_history(
        symbol="TEST",
        as_of_date="2025-12-31",
        limit=12,
    )

    assert len(periods) == 8

    end_dates = [
        period.end_date
        for period in periods
    ]

    assert end_dates == sorted(
        end_dates
    )

    revenue_values = [
        period.revenue
        for period in periods
    ]

    assert revenue_values == [
        100.0,
        110.0,
        120.0,
        130.0,
        140.0,
        150.0,
        160.0,
        200.0,
    ]


# ============================================================
# TEST: CONTEXT TTM QOQ / YOY
# ============================================================

def test_context_ttm_uses_correct_qoq_and_yoy():
    period_data = [
        (
            "2023-01-01",
            "2023-03-31",
            "2023-05-01",
            2023,
            "Q1",
            100.0,
        ),
        (
            "2023-04-01",
            "2023-06-30",
            "2023-08-01",
            2023,
            "Q2",
            110.0,
        ),
        (
            "2023-07-01",
            "2023-09-30",
            "2023-11-01",
            2023,
            "Q3",
            120.0,
        ),
        (
            "2023-10-01",
            "2023-12-31",
            "2024-02-01",
            2023,
            "Q4",
            130.0,
        ),
        (
            "2024-01-01",
            "2024-03-31",
            "2024-05-01",
            2024,
            "Q1",
            140.0,
        ),
        (
            "2024-04-01",
            "2024-06-30",
            "2024-08-01",
            2024,
            "Q2",
            150.0,
        ),
        (
            "2024-07-01",
            "2024-09-30",
            "2024-11-01",
            2024,
            "Q3",
            160.0,
        ),
        (
            "2024-10-01",
            "2024-12-31",
            "2025-02-01",
            2024,
            "Q4",
            200.0,
        ),
    ]

    periods = [
        FinancialPeriod(
            symbol="TEST",
            start_date=start_date,
            end_date=end_date,
            filed_date=filed_date,
            form=(
                "10-K"
                if fiscal_period == "Q4"
                else "10-Q"
            ),
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            revenue=value,
            net_income=value,
            eps=value,
            operating_cash_flow=None,
            capital_expenditure=None,
            free_cash_flow=None,
        )
        for (
            start_date,
            end_date,
            filed_date,
            fiscal_year,
            fiscal_period,
            value,
        ) in period_data
    ]

    ttm = (
        FundamentalContextEngine
        ._build_ttm(
            periods=periods,
            as_of_date="2024-12-31",
        )
    )

    assert ttm is not None

    # --------------------------------------------------------
    # Current TTM:
    #
    # 140 + 150 + 160 + 200 = 650
    # --------------------------------------------------------

    assert ttm.revenue_ttm == 650.0

    # --------------------------------------------------------
    # QoQ:
    #
    # latest       = 200
    # previous     = 160
    #
    # 200 / 160 - 1 = 25%
    # --------------------------------------------------------

    assert ttm.revenue_qoq is not None

    assert abs(
        ttm.revenue_qoq - 0.25
    ) < 1e-9

    # --------------------------------------------------------
    # YoY:
    #
    # latest       = 200
    # year ago     = 130
    #
    # 200 / 130 - 1
    # --------------------------------------------------------

    expected_yoy = (
        200.0 / 130.0
    ) - 1.0

    assert ttm.revenue_yoy is not None

    assert abs(
        ttm.revenue_yoy - expected_yoy
    ) < 1e-9


# ============================================================
# TEST: FINANCIAL STATEMENT ENGINE TTM
# ============================================================

def test_financial_statement_engine_ttm_uses_correct_qoq():

    facts = build_revenue_facts()

    fake_data = FakeFundamentalData(
        facts
    )

    engine = FinancialStatementEngine(
        fake_data
    )

    ttm = engine.get_ttm(
        symbol="TEST",
        as_of_date="2025-12-31",
    )

    assert ttm is not None

    # --------------------------------------------------------
    # Last four quarters:
    #
    # 140 + 150 + 160 + 200 = 650
    # --------------------------------------------------------

    assert ttm.revenue_ttm == 650.0

    # --------------------------------------------------------
    # QoQ:
    #
    # 200 / 160 - 1 = 25%
    # --------------------------------------------------------

    assert ttm.revenue_qoq is not None

    assert abs(
        ttm.revenue_qoq - 0.25
    ) < 1e-9

    # --------------------------------------------------------
    # YoY:
    #
    # 200 / 130 - 1
    # --------------------------------------------------------

    expected_yoy = (
        200.0 / 130.0
    ) - 1.0

    assert ttm.revenue_yoy is not None

    assert abs(
        ttm.revenue_yoy - expected_yoy
    ) < 1e-9