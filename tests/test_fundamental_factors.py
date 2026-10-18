from datetime import date
from data.financial_statement import TTMFinancials

import pytest

from data.fundamental_data import FundamentalSnapshot
from strategy.fundamental_factors import (
    FundamentalFactorEngine,
)


def make_snapshot(
    symbol="AAPL",
    revenue=1000.0,
    net_income=200.0,
    eps=2.0,
    net_margin=0.20,
    roe=0.20,
    fcf_margin=0.15,
    debt_to_assets=0.30,
    cash_to_assets=0.20,
    filing_date="2025-05-01",
):

    return FundamentalSnapshot(

        symbol=symbol,

        as_of_date="2025-05-15",

        report_date="2025-03-31",

        filing_date=filing_date,

        revenue=revenue,

        net_income=net_income,

        total_assets=5000.0,

        total_liabilities=1500.0,

        stockholders_equity=3500.0,

        cash=1000.0,

        operating_cash_flow=250.0,

        capital_expenditure=100.0,

        eps=eps,

        net_margin=net_margin,

        return_on_equity=roe,

        debt_to_assets=debt_to_assets,

        cash_to_assets=cash_to_assets,

        free_cash_flow=150.0,

        free_cash_flow_margin=fcf_margin,
    )


# ============================================================
# GROWTH
# ============================================================

def test_growth_calculation():

    engine = FundamentalFactorEngine()

    result = engine._growth(
        120,
        100,
    )

    assert result == pytest.approx(0.20)


def test_growth_zero_previous():

    engine = FundamentalFactorEngine()

    result = engine._growth(
        120,
        0,
    )

    assert result is None


# ============================================================
# SCORES
# ============================================================

def test_positive_growth_score_is_positive():

    score = (
        FundamentalFactorEngine.score_growth(
            0.20
        )
    )

    assert score > 80


def test_negative_growth_score_is_low():

    score = (
        FundamentalFactorEngine.score_growth(
            -0.20
        )
    )

    assert score <= 20


def test_high_roe_score():

    score = (
        FundamentalFactorEngine.score_roe(
            0.25
        )
    )

    assert score == 100


def test_high_debt_has_low_score():

    score = (
        FundamentalFactorEngine.score_debt(
            0.90
        )
    )

    assert score <= 10


def test_high_cash_score():

    score = (
        FundamentalFactorEngine.score_cash(
            0.20
        )
    )

    assert score >= 95


# ============================================================
# FULL FACTOR ENGINE
# ============================================================

def test_strong_company_gets_high_score():

    current = make_snapshot(

        revenue=1200.0,

        net_income=280.0,

        eps=2.40,

        net_margin=0.25,

        roe=0.25,

        fcf_margin=0.20,

        debt_to_assets=0.20,

        cash_to_assets=0.20,
    )

    previous = make_snapshot(

        revenue=1000.0,

        net_income=200.0,

        eps=2.00,

        net_margin=0.20,

        roe=0.20,

        fcf_margin=0.15,

        debt_to_assets=0.25,

        cash_to_assets=0.15,
    )

    engine = FundamentalFactorEngine()

    result = engine.calculate(
        current,
        previous,
    )

    assert result.symbol == "AAPL"

    assert result.revenue_growth == pytest.approx(0.20)

    assert result.net_income_growth == pytest.approx(0.40)

    assert result.eps_growth == pytest.approx(0.20)

    assert result.fundamental_score >= 75


def test_weak_company_gets_lower_score():

    current = make_snapshot(

        revenue=800.0,

        net_income=50.0,

        eps=0.80,

        net_margin=0.02,

        roe=0.02,

        fcf_margin=0.01,

        debt_to_assets=0.80,

        cash_to_assets=0.02,
    )

    previous = make_snapshot(

        revenue=1000.0,

        net_income=200.0,

        eps=2.00,
    )

    engine = FundamentalFactorEngine()

    result = engine.calculate(
        current,
        previous,
    )

    assert result.fundamental_score < 50


def test_missing_previous_snapshot():

    current = make_snapshot()

    engine = FundamentalFactorEngine()

    result = engine.calculate(
        current,
        None,
    )

    assert result.revenue_growth is None

    assert result.net_income_growth is None

    assert result.eps_growth is None

    assert result.fundamental_score >= 0


def test_earnings_quality():

    current = make_snapshot(
        net_income=200.0,
    )

    engine = FundamentalFactorEngine()

    result = engine.calculate(
        current
    )

    assert result.earnings_quality == pytest.approx(0.75)


def test_data_quality():

    current = make_snapshot()

    engine = FundamentalFactorEngine()

    result = engine.calculate(
        current
    )

    assert result.data_quality_score == 100.0


# ============================================================
# DATE IMPORT / SANITY
# ============================================================

def test_date_import_is_available():
    value = date(2025, 1, 15)

    assert value.isoformat() == "2025-01-15"


def make_ttm(
    symbol="AAPL",
    revenue=460.0,
    net_income=70.0,
    eps=4.6,
    fcf=35.0,
    revenue_qoq=0.10,
    net_income_qoq=0.10,
    eps_qoq=0.10,
):
    return TTMFinancials(
        symbol=symbol,
        as_of_date="2025-12-31",
        latest_quarter_end="2025-12-31",
        revenue_ttm=revenue,
        net_income_ttm=net_income,
        eps_ttm=eps,
        operating_cash_flow_ttm=fcf + 50,
        capital_expenditure_ttm=50.0,
        free_cash_flow_ttm=fcf,
        revenue_qoq=revenue_qoq,
        revenue_yoy=0.10,
        net_income_qoq=net_income_qoq,
        net_income_yoy=0.15,
        eps_qoq=eps_qoq,
        eps_yoy=0.12,
        fcf_yoy=0.20,
    )


def test_ttm_growth_calculation():
    engine = FundamentalFactorEngine()

    current = make_ttm(
        revenue=600.0,
        net_income=90.0,
        eps=6.0,
        fcf=50.0,
    )

    previous = make_ttm(
        revenue=500.0,
        net_income=75.0,
        eps=5.0,
        fcf=40.0,
    )

    result = engine.calculate_from_ttm(
        current_ttm=current,
        previous_ttm=previous,
    )

    assert result.revenue_ttm_growth == pytest.approx(0.20)
    assert result.net_income_ttm_growth == pytest.approx(0.20)
    assert result.eps_ttm_growth == pytest.approx(0.20)
    assert result.fcf_ttm_growth == pytest.approx(0.25)


def test_ttm_fcf_margin():
    engine = FundamentalFactorEngine()

    current = make_ttm(
        revenue=500.0,
        fcf=100.0,
    )

    result = engine.calculate_from_ttm(
        current_ttm=current,
        previous_ttm=None,
    )

    assert result.free_cash_flow_margin == pytest.approx(0.20)


def test_ttm_earnings_quality():
    engine = FundamentalFactorEngine()

    current = make_ttm(
        net_income=100.0,
        fcf=100.0,
    )

    result = engine.calculate_from_ttm(
        current_ttm=current,
        previous_ttm=None,
    )

    assert result.earnings_quality == pytest.approx(1.0)


def test_ttm_with_snapshot_uses_profitability():
    engine = FundamentalFactorEngine()

    current = make_ttm()

    snapshot = make_snapshot(
        net_margin=0.25,
        roe=0.25,
        debt_to_assets=0.20,
        cash_to_assets=0.20,
    )

    result = engine.calculate_from_ttm(
        current_ttm=current,
        previous_ttm=None,
        snapshot=snapshot,
    )

    assert result.net_margin == 0.25
    assert result.roe == 0.25
    assert result.debt_to_assets == 0.20
    assert result.cash_to_assets == 0.20
    assert result.profitability_score > 80
    assert result.balance_sheet_score > 90


def test_ttm_result_has_final_score():
    engine = FundamentalFactorEngine()

    current = make_ttm(
        revenue=600.0,
        net_income=100.0,
        eps=6.0,
        fcf=100.0,
    )

    previous = make_ttm(
        revenue=500.0,
        net_income=80.0,
        eps=5.0,
        fcf=80.0,
    )

    snapshot = make_snapshot(
        net_margin=0.20,
        roe=0.20,
        debt_to_assets=0.20,
        cash_to_assets=0.20,
    )

    result = engine.calculate_from_ttm(
        current_ttm=current,
        previous_ttm=previous,
        snapshot=snapshot,
    )

    assert 0 <= result.fundamental_score <= 100
    assert result.data_quality_score > 80


def test_ttm_missing_previous_has_no_ttm_growth():
    engine = FundamentalFactorEngine()

    current = make_ttm()

    result = engine.calculate_from_ttm(
        current_ttm=current,
        previous_ttm=None,
    )

    assert result.revenue_ttm_growth is None
    assert result.net_income_ttm_growth is None
    assert result.eps_ttm_growth is None
    assert result.fcf_ttm_growth is None


def test_ttm_growth_negative():
    engine = FundamentalFactorEngine()

    current = make_ttm(
        revenue=400.0,
    )

    previous = make_ttm(
        revenue=500.0,
    )

    result = engine.calculate_from_ttm(
        current_ttm=current,
        previous_ttm=previous,
    )

    assert result.revenue_ttm_growth == pytest.approx(-0.20)
    assert result.growth_score < 60


def test_growth_positive_to_positive():
    assert FundamentalFactorEngine._growth(120, 100) == pytest.approx(0.20)


def test_growth_negative_to_less_negative_is_positive():
    assert FundamentalFactorEngine._growth(-100, -200) == 0.50


def test_growth_negative_to_more_negative_is_negative():
    assert FundamentalFactorEngine._growth(-300, -200) == -0.50


def test_growth_zero_crossing_returns_none():
    assert FundamentalFactorEngine._growth(100, -100) is None
    assert FundamentalFactorEngine._growth(-100, 100) is None


def test_ttm_growth_uses_sign_aware_logic():
    assert (
        FundamentalFactorEngine._ttm_growth(-100, -200)
        == 0.50
    )