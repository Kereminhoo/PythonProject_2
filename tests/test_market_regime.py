import pandas as pd

from regime.market_regime import (
    MarketRegime,
    MarketRegimeEngine,
)


class FakeSettings:
    pass


def create_base_data(
    close=100.0,
    ema_9=102.0,
    ema_21=100.0,
    atr=0.5,
    return_3=0.01,
    return_6=0.02,
):
    rows = []

    for _ in range(40):

        rows.append({
            "close": close,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "atr": atr,
            "return_3": return_3,
            "return_6": return_6,
        })

    return pd.DataFrame(rows)


# ============================================================
# TEST 1
# ============================================================

def test_bull_regime():

    engine = MarketRegimeEngine(
        FakeSettings()
    )

    df = create_base_data(
        close=105.0,
        ema_9=104.0,
        ema_21=100.0,
        atr=0.5,
        return_3=0.01,
        return_6=0.02,
    )

    result = engine.evaluate(df)

    assert result.regime == MarketRegime.BULL


# ============================================================
# TEST 2
# ============================================================

def test_bear_regime():

    engine = MarketRegimeEngine(
        FakeSettings()
    )

    df = create_base_data(
        close=95.0,
        ema_9=96.0,
        ema_21=100.0,
        atr=0.5,
        return_3=-0.01,
        return_6=-0.02,
    )

    result = engine.evaluate(df)

    assert result.regime == MarketRegime.BEAR


# ============================================================
# TEST 3
# ============================================================

def test_sideways_regime():

    engine = MarketRegimeEngine(
        FakeSettings()
    )

    df = create_base_data(
        close=100.0,
        ema_9=100.0,
        ema_21=100.0,
        atr=0.5,
        return_3=0.0,
        return_6=0.0,
    )

    result = engine.evaluate(df)

    assert result.regime == MarketRegime.SIDEWAYS


# ============================================================
# TEST 4
# ============================================================

def test_high_volatility_regime():

    engine = MarketRegimeEngine(
        FakeSettings()
    )

    df = create_base_data(
        close=100.0,
        ema_9=102.0,
        ema_21=100.0,
        atr=1.5,
        return_3=0.01,
        return_6=0.02,
    )

    result = engine.evaluate(df)

    assert result.regime == MarketRegime.HIGH_VOLATILITY


# ============================================================
# TEST 5
# ============================================================

def test_insufficient_data():

    engine = MarketRegimeEngine(
        FakeSettings()
    )

    df = pd.DataFrame({
        "close": [100.0],
        "ema_9": [101.0],
        "ema_21": [100.0],
        "atr": [0.5],
        "return_3": [0.01],
        "return_6": [0.02],
    })

    result = engine.evaluate(df)

    assert result.regime == MarketRegime.UNKNOWN


# ============================================================
# TEST 6
# ============================================================

def test_missing_indicator():

    engine = MarketRegimeEngine(
        FakeSettings()
    )

    df = create_base_data()

    df = df.drop(
        columns=["atr"]
    )

    result = engine.evaluate(df)

    assert result.regime == MarketRegime.UNKNOWN