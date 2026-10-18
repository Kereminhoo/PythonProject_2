import pytest

from strategy.alpha_engine import (
    CombinedAlphaEngine,
)


# ============================================================
# WEIGHTS
# ============================================================

def test_default_weights_sum_to_one():

    engine = CombinedAlphaEngine()

    assert (
        engine.technical_weight
        + engine.fundamental_weight
    ) == pytest.approx(1.0)

    assert (
        engine.technical_weight
        == pytest.approx(0.65)
    )

    assert (
        engine.fundamental_weight
        == pytest.approx(0.35)
    )


def test_custom_weights_are_normalized():

    engine = CombinedAlphaEngine(
        technical_weight=2,
        fundamental_weight=1,
    )

    assert (
        engine.technical_weight
        == pytest.approx(2 / 3)
    )

    assert (
        engine.fundamental_weight
        == pytest.approx(1 / 3)
    )


# ============================================================
# VALIDATION
# ============================================================

def test_negative_weight_rejected():

    with pytest.raises(ValueError):

        CombinedAlphaEngine(
            technical_weight=-1,
            fundamental_weight=1,
        )


def test_zero_weights_rejected():

    with pytest.raises(ValueError):

        CombinedAlphaEngine(
            technical_weight=0,
            fundamental_weight=0,
        )


# ============================================================
# BASIC COMBINATION
# ============================================================

def test_combines_technical_and_fundamental():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="AAPL",
        technical_score=80,
        fundamental_score=60,
        regime="SIDEWAYS",
    )

    expected = (
        80 * 0.65
        + 60 * 0.35
    )

    assert (
        result.base_score
        == pytest.approx(expected)
    )

    assert (
        result.final_score
        == pytest.approx(expected)
    )


# ============================================================
# REGIME
# ============================================================

def test_bull_regime_bonus():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="AAPL",
        technical_score=80,
        fundamental_score=80,
        regime="BULL",
    )

    assert result.base_score == pytest.approx(
        80
    )

    assert result.regime_adjustment == 5.0

    assert result.final_score == pytest.approx(
        85
    )


def test_bear_regime_penalty():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="TSLA",
        technical_score=80,
        fundamental_score=80,
        regime="BEAR",
    )

    assert result.base_score == pytest.approx(
        80
    )

    assert result.regime_adjustment == -15.0

    assert result.final_score == pytest.approx(
        65
    )


def test_high_volatility_penalty():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="NVDA",
        technical_score=80,
        fundamental_score=80,
        regime="HIGH_VOLATILITY",
    )

    assert result.final_score == pytest.approx(
        75
    )


def test_sideways_has_no_adjustment():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="MSFT",
        technical_score=80,
        fundamental_score=80,
        regime="SIDEWAYS",
    )

    assert result.regime_adjustment == 0.0

    assert result.final_score == pytest.approx(
        80
    )


# ============================================================
# FUNDAMENTAL MISSING
# ============================================================

def test_missing_fundamental_does_not_zero_score():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="AAPL",
        technical_score=80,
        fundamental_score=None,
        regime="SIDEWAYS",
    )

    assert result.base_score == pytest.approx(
        80
    )

    assert result.final_score == pytest.approx(
        80
    )

    assert result.eligible is True


def test_missing_fundamental_is_reported():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="AAPL",
        technical_score=80,
        fundamental_score=None,
    )

    assert (
        "fundamental data unavailable"
        in result.reason
    )


# ============================================================
# DATA QUALITY
# ============================================================

def test_low_data_quality_blocks_candidate():

    engine = CombinedAlphaEngine(
        minimum_data_quality=60
    )

    result = engine.calculate(
        symbol="AAPL",
        technical_score=80,
        fundamental_score=85,
        data_quality_score=40,
    )

    assert result.eligible is False

    assert (
        "insufficient fundamental data quality"
        in result.reason
    )


def test_good_data_quality_allows_candidate():

    engine = CombinedAlphaEngine(
        minimum_data_quality=60
    )

    result = engine.calculate(
        symbol="AAPL",
        technical_score=80,
        fundamental_score=85,
        data_quality_score=80,
    )

    assert result.eligible is True


# ============================================================
# SCORE CLAMP
# ============================================================

def test_high_scores_are_clamped():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="AAPL",
        technical_score=150,
        fundamental_score=150,
        regime="BULL",
    )

    assert result.technical_score == 100.0

    assert result.fundamental_score == 100.0

    assert result.final_score == 100.0


def test_low_scores_are_clamped():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="AAPL",
        technical_score=-20,
        fundamental_score=-10,
        regime="BEAR",
    )

    assert result.technical_score == 0.0

    assert result.fundamental_score == 0.0

    assert result.final_score == 0.0


# ============================================================
# UNKNOWN REGIME
# ============================================================

def test_unknown_regime_no_adjustment():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="AAPL",
        technical_score=70,
        fundamental_score=70,
        regime="UNKNOWN",
    )

    assert result.regime == "UNKNOWN"

    assert result.regime_adjustment == 0.0

    assert result.final_score == pytest.approx(
        70
    )


# ============================================================
# RESULT STRUCTURE
# ============================================================

def test_result_structure():

    engine = CombinedAlphaEngine()

    result = engine.calculate(
        symbol="MSFT",
        technical_score=70,
        fundamental_score=75,
        regime="BULL",
        data_quality_score=90,
    )

    assert result.symbol == "MSFT"

    assert result.technical_score == 70

    assert result.fundamental_score == 75

    assert result.regime == "BULL"

    assert result.data_quality_score == 90

    assert result.eligible is True