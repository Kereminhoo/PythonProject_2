import pytest

from data.fundamental_data import FundamentalData
from data.financial_statement import (
    FinancialPeriod,
    FinancialStatementEngine,
)


def make_period(
    end_date,
    revenue,
    net_income,
    eps,
    fcf,
    fiscal_year=2025,
    fiscal_period="Q1",
):
    starts = {
        "Q1": "01-01",
        "Q2": "04-01",
        "Q3": "07-01",
        "Q4": "10-01",
    }

    start = starts[fiscal_period]

    year = end_date[:4]

    return FinancialPeriod(

        symbol="AAPL",

        start_date=f"{year}-{start}",

        end_date=end_date,

        filed_date="2025-05-01",

        form=(
            "10-Q"
            if fiscal_period != "Q4"
            else "10-K"
        ),

        fiscal_year=fiscal_year,

        fiscal_period=fiscal_period,

        revenue=revenue,

        net_income=net_income,

        eps=eps,

        operating_cash_flow=(
            fcf + 50
        ),

        capital_expenditure=50,

        free_cash_flow=fcf,
    )


def make_engine():

    fundamental = FundamentalData()

    return FinancialStatementEngine(
        fundamental
    )


# ============================================================
# DURATION
# ============================================================

def test_quarter_duration():

    engine = make_engine()

    days = engine._duration_days(
        "2025-01-01",
        "2025-03-31",
    )

    assert 89 <= days <= 91


def test_invalid_duration():

    engine = make_engine()

    days = engine._duration_days(
        None,
        "2025-03-31",
    )

    assert days is None


# ============================================================
# GROWTH
# ============================================================

def test_growth():

    engine = make_engine()

    result = engine._growth(
        120,
        100,
    )

    assert result == pytest.approx(
        0.2
    )


def test_growth_zero():

    engine = make_engine()

    result = engine._growth(
        120,
        0,
    )

    assert result is None


# ============================================================
# AS-OF FILTER
# ============================================================

def test_as_of_entries():

    entries = [

        {
            "val": 100,
            "filed": "2025-01-10",
        },

        {
            "val": 200,
            "filed": "2025-02-10",
        },
    ]

    result = (
        FinancialStatementEngine
        ._as_of_entries(
            entries,
            "2025-01-31",
        )
    )

    assert len(result) == 1

    assert result[0]["val"] == 100


# ============================================================
# DEDUPLICATION
# ============================================================

def test_deduplicate_periods_uses_latest_filing():

    entries = [

        {
            "start": "2025-01-01",
            "end": "2025-03-31",
            "filed": "2025-05-01",
            "val": 100,
            "fy": 2025,
            "fp": "Q1",
        },

        {
            "start": "2025-01-01",
            "end": "2025-03-31",
            "filed": "2025-05-15",
            "val": 110,
            "fy": 2025,
            "fp": "Q1",
        },
    ]

    result = (
        FinancialStatementEngine
        ._deduplicate_periods(
            entries,
            "2025-06-01",
        )
    )

    assert len(result) == 1

    assert result[0]["val"] == 110


def test_future_amendment_is_not_used():

    entries = [

        {
            "start": "2025-01-01",
            "end": "2025-03-31",
            "filed": "2025-05-01",
            "val": 100,
            "fy": 2025,
            "fp": "Q1",
        },

        {
            "start": "2025-01-01",
            "end": "2025-03-31",
            "filed": "2025-08-01",
            "val": 110,
            "fy": 2025,
            "fp": "Q1",
        },
    ]

    result = (
        FinancialStatementEngine
        ._deduplicate_periods(
            entries,
            "2025-06-01",
        )
    )

    assert len(result) == 1

    assert result[0]["val"] == 100


# ============================================================
# ANNUAL DETECTION
# ============================================================

def test_annual_duration():

    engine = make_engine()

    entries = [

        {
            "start": "2025-01-01",
            "end": "2025-12-31",
            "filed": "2026-02-10",
            "form": "10-K",
            "fy": 2025,
            "fp": "FY",
            "val": 1000,
        },

        {
            "start": "2025-01-01",
            "end": "2025-03-31",
            "filed": "2025-05-01",
            "form": "10-Q",
            "fy": 2025,
            "fp": "Q1",
            "val": 200,
        },
    ]

    result = (
        engine._annual_entries(
            {
                "units": {
                    "USD": entries
                }
            },
            "2026-03-01",
        )
    )

    assert len(result) == 1

    assert result[0]["fp"] == "FY"


# ============================================================
# TTM SUM
# ============================================================

def test_ttm_sum():

    periods = [

        make_period(
            "2025-03-31",
            100,
            10,
            1,
            8,
        ),

        make_period(
            "2025-06-30",
            110,
            12,
            1.1,
            9,
            fiscal_period="Q2",
        ),

        make_period(
            "2025-09-30",
            120,
            14,
            1.2,
            10,
            fiscal_period="Q3",
        ),

        make_period(
            "2025-12-31",
            130,
            16,
            1.3,
            11,
            fiscal_period="Q4",
        ),
    ]

    engine = make_engine()

    assert (
        engine._ttm_sum(
            periods,
            "revenue",
        )
        == 460
    )


def test_ttm_requires_four_periods():

    periods = [

        make_period(
            "2025-03-31",
            100,
            10,
            1,
            8,
        ),

        make_period(
            "2025-06-30",
            110,
            12,
            1.1,
            9,
            fiscal_period="Q2",
        ),
    ]

    engine = make_engine()

    result = engine._ttm_sum(
        periods,
        "revenue",
    )

    assert result is None


# ============================================================
# Q4 DERIVATION
# ============================================================

def test_q4_is_derived_from_annual_minus_q1_q2_q3():

    engine = make_engine()

    annual = {
        "start": "2025-01-01",
        "end": "2025-12-31",
        "filed": "2026-02-01",
        "form": "10-K",
        "fy": 2025,
        "fp": "FY",
        "_revenue": 1000.0,
        "_net_income": 100.0,
        "_operating_cash_flow": 180.0,
        "_capital_expenditure": 40.0,
    }

    q1 = {
        "start": "2025-01-01",
        "end": "2025-03-31",
        "filed": "2025-05-01",
        "_revenue": 200.0,
        "_net_income": 20.0,
        "_operating_cash_flow": 40.0,
        "_capital_expenditure": 10.0,
    }

    q2 = {
        "start": "2025-04-01",
        "end": "2025-06-30",
        "filed": "2025-08-01",
        "_revenue": 230.0,
        "_net_income": 25.0,
        "_operating_cash_flow": 45.0,
        "_capital_expenditure": 10.0,
    }

    q3 = {
        "start": "2025-07-01",
        "end": "2025-09-30",
        "filed": "2025-11-01",
        "_revenue": 250.0,
        "_net_income": 30.0,
        "_operating_cash_flow": 50.0,
        "_capital_expenditure": 10.0,
    }

    q4 = (
        engine._derive_q4_entry(
            annual,
            q1,
            q2,
            q3,
        )
    )

    assert q4 is not None

    assert q4["revenue"] == pytest.approx(
        320.0
    )

    assert q4["net_income"] == pytest.approx(
        25.0
    )

    assert (
        q4["operating_cash_flow"]
        == pytest.approx(45.0)
    )

    assert (
        q4["capital_expenditure"]
        == pytest.approx(10.0)
    )

    assert (
        q4["free_cash_flow"]
        == pytest.approx(35.0)
    )

    # EPS intentionally not derived.
    assert q4["eps"] is None

    assert q4["fp"] == "Q4"


def test_q4_start_is_day_after_q3():

    engine = make_engine()

    annual = {
        "start": "2025-01-01",
        "end": "2025-12-31",
        "filed": "2026-02-01",
        "form": "10-K",
        "fy": 2025,
        "fp": "FY",
        "_revenue": 1000.0,
        "_net_income": 100.0,
        "_operating_cash_flow": 180.0,
        "_capital_expenditure": 40.0,
    }

    q1 = {
        "start": "2025-01-01",
        "end": "2025-03-31",
        "_revenue": 200.0,
        "_net_income": 20.0,
        "_operating_cash_flow": 40.0,
        "_capital_expenditure": 10.0,
    }

    q2 = {
        "start": "2025-04-01",
        "end": "2025-06-30",
        "_revenue": 230.0,
        "_net_income": 25.0,
        "_operating_cash_flow": 45.0,
        "_capital_expenditure": 10.0,
    }

    q3 = {
        "start": "2025-07-01",
        "end": "2025-09-30",
        "_revenue": 250.0,
        "_net_income": 30.0,
        "_operating_cash_flow": 50.0,
        "_capital_expenditure": 10.0,
    }

    q4 = (
        engine._derive_q4_entry(
            annual,
            q1,
            q2,
            q3,
        )
    )

    assert q4["start"] == "2025-10-01"

    assert q4["end"] == "2025-12-31"


# ============================================================
# EPS SAFETY
# ============================================================

def test_ttm_eps_returns_none_when_derived_q4_has_no_eps():

    periods = [

        make_period(
            "2025-03-31",
            100,
            10,
            1.0,
            8,
        ),

        make_period(
            "2025-06-30",
            110,
            12,
            1.1,
            9,
            fiscal_period="Q2",
        ),

        make_period(
            "2025-09-30",
            120,
            14,
            1.2,
            10,
            fiscal_period="Q3",
        ),

        make_period(
            "2025-12-31",
            130,
            16,
            None,
            11,
            fiscal_period="Q4",
        ),
    ]

    engine = make_engine()

    result = engine._ttm_sum(
        periods,
        "eps",
    )

    assert result is None


# ============================================================
# FINANCIAL PERIOD
# ============================================================

def test_financial_period():

    period = make_period(
        "2025-03-31",
        100,
        10,
        1,
        8,
    )

    assert period.symbol == "AAPL"

    assert period.revenue == 100

    assert period.net_income == 10

    assert period.eps == 1

    assert period.free_cash_flow == 8


# ============================================================
# IMPORT / DEPENDENCY
# ============================================================

def test_engine_uses_fundamental_data():

    fundamental = FundamentalData()

    engine = FinancialStatementEngine(
        fundamental
    )

    assert (
        engine.fundamental_data
        is fundamental
    )


# ============================================================
# TTM CONTINUITY
# ============================================================

def test_ttm_requires_continuous_quarters():

    periods = [

        make_period(
            "2025-03-31",
            100,
            10,
            1.0,
            8,
            fiscal_period="Q1",
        ),

        make_period(
            "2025-06-30",
            110,
            12,
            1.1,
            9,
            fiscal_period="Q2",
        ),

        make_period(
            "2025-09-30",
            120,
            14,
            1.2,
            10,
            fiscal_period="Q3",
        ),

        make_period(
            "2025-12-31",
            130,
            16,
            1.3,
            11,
            fiscal_period="Q4",
        ),
    ]

    engine = make_engine()

    selected = (
        engine._select_ttm_periods(
            periods
        )
    )

    assert selected is not None
    assert len(selected) == 4


def test_ttm_rejects_missing_quarter():

    periods = [

        make_period(
            "2025-03-31",
            100,
            10,
            1.0,
            8,
            fiscal_period="Q1",
        ),

        # Q2 intentionally missing.

        make_period(
            "2025-09-30",
            120,
            14,
            1.2,
            10,
            fiscal_period="Q3",
        ),

        make_period(
            "2025-12-31",
            130,
            16,
            1.3,
            11,
            fiscal_period="Q4",
        ),

        make_period(
            "2026-03-31",
            140,
            18,
            1.4,
            12,
            fiscal_year=2026,
            fiscal_period="Q1",
        ),
    ]

    engine = make_engine()

    selected = (
        engine._select_ttm_periods(
            periods
        )
    )

    assert selected is None


# ============================================================
# SIGN-AWARE GROWTH
# ============================================================

def test_negative_to_less_negative_growth_is_positive():

    engine = make_engine()

    result = engine._growth(
        -100,
        -200,
    )

    assert result == pytest.approx(
        0.50
    )


def test_negative_to_more_negative_growth_is_negative():

    engine = make_engine()

    result = engine._growth(
        -300,
        -200,
    )

    assert result == pytest.approx(
        -0.50
    )


def test_zero_crossing_growth_is_none():

    engine = make_engine()

    negative_to_positive = engine._growth(
        100,
        -100,
    )

    positive_to_negative = engine._growth(
        -100,
        100,
    )

    assert negative_to_positive is None
    assert positive_to_negative is None