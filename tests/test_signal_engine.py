import pandas as pd

from strategy.signal_engine import (
    Signal,
    SignalEngine,
    SignalResult,
)


class FakeSettings:
    minimum_buy_score = 75


def make_dataframe(
    *,
    price_vs_vwap=0.002,
    macd_strength=0.25,
    ema_gap_pct=0.003,
    rsi=60.0,
    volume_ratio=1.5,
    macd_cross=True,
    ema_cross=True,

    # ========================================================
    # V3 FEATURES
    # ========================================================

    ema_5_7_bullish=True,
    ema_5_slope=0.10,
    ema_7_slope=0.05,

    sma_20_slope=0.10,
    price_vs_sma20=0.003,

    zl_macd=0.20,
    zl_macd_signal=0.10,
    zl_macd_histogram=0.10,
    zl_macd_slope=0.05,
    zl_macd_signal_slope=0.02,

    ichimoku_cloud_bullish=True,
    ichimoku_price_above_cloud=True,
    ichimoku_tenkan_above_kijun=True,

    chikou_bullish=True,

    adx=25.0,
    adx_slope=0.50,
    di_plus=30.0,
    di_minus=20.0,
    dmi_bullish=True,

    obv_sma=1000.0,
    obv_slope=100.0,
    obv_bullish=True,

    cmf=0.10,
    cmf_slope=0.01,
    cmf_bullish=True,

    atr_pct=0.01,
    atr_slope=0.001,
    atr_pct_change=0.05,

    bb_middle_slope=0.05,
    bb_width=0.04,
    bb_width_change=0.001,
    price_vs_bb_middle=0.003,

    relative_volume_at_time=1.5,

    candle_bullish=True,
    candle_body_pct=0.70,
    candle_close_position=0.80,

    breakout_above_10=True,
):
    rows = []

    for _ in range(30):

        rows.append(
            {
                # ==================================================
                # LEGACY
                # ==================================================

                "macd": 0.20,
                "macd_signal": 0.10,
                "ema_9": 100.50,
                "ema_21": 100.00,
                "ema_gap_pct": 0.005,

                "rsi": rsi,
                "volume_ratio": volume_ratio,

                "macd_histogram": 0.10,
                "macd_strength": macd_strength,

                "price_vs_vwap": price_vs_vwap,

                # ==================================================
                # EMA 5 / 7
                # ==================================================

                "ema_5": 100.50,
                "ema_7": 100.00,

                "ema_5_slope": ema_5_slope,
                "ema_7_slope": ema_7_slope,

                "ema_5_7_gap_pct": 0.005,

                # ==================================================
                # SMA 20
                # ==================================================

                "sma_20": 100.00,
                "sma_20_slope": sma_20_slope,
                "price_vs_sma20": price_vs_sma20,

                # ==================================================
                # BOLLINGER
                # ==================================================

                "bb_middle": 100.00,
                "bb_upper": 102.00,
                "bb_lower": 98.00,

                "bb_pct_b": 0.75,
                "bb_width": bb_width,
                "bb_middle_slope": bb_middle_slope,
                "bb_width_change": bb_width_change,
                "price_vs_bb_middle": price_vs_bb_middle,

                # ==================================================
                # ICHIMOKU
                # ==================================================

                "ichimoku_tenkan": 101.00,
                "ichimoku_kijun": 100.00,

                "ichimoku_span_a": 101.00,
                "ichimoku_span_b": 99.00,

                "ichimoku_cloud_top": 101.00,
                "ichimoku_cloud_bottom": 99.00,

                "ichimoku_cloud_width": 2.00,

                "ichimoku_cloud_bullish":
                    ichimoku_cloud_bullish,

                "ichimoku_price_above_cloud":
                    ichimoku_price_above_cloud,

                "ichimoku_tenkan_above_kijun":
                    ichimoku_tenkan_above_kijun,

                # ==================================================
                # CHIKOU
                # ==================================================

                "chikou_close": 100.50,
                "chikou_bullish": chikou_bullish,

                # ==================================================
                # ADX / DMI
                # ==================================================

                "adx": adx,
                "di_plus": di_plus,
                "di_minus": di_minus,

                "adx_slope": adx_slope,
                "dmi_bullish": dmi_bullish,

                # ==================================================
                # OBV
                # ==================================================

                "obv": 1100.0,
                "obv_sma": obv_sma,
                "obv_slope": obv_slope,
                "obv_bullish": obv_bullish,

                # ==================================================
                # CMF
                # ==================================================

                "cmf": cmf,
                "cmf_slope": cmf_slope,
                "cmf_bullish": cmf_bullish,

                # ==================================================
                # ATR
                # ==================================================

                "atr": 1.00,
                "atr_pct": atr_pct,
                "atr_slope": atr_slope,
                "atr_pct_change": atr_pct_change,

                # ==================================================
                # ZERO-LAG MACD
                # ==================================================

                "zl_macd": zl_macd,
                "zl_macd_signal": zl_macd_signal,
                "zl_macd_histogram": zl_macd_histogram,

                "zl_macd_slope": zl_macd_slope,
                "zl_macd_signal_slope":
                    zl_macd_signal_slope,

                "zl_macd_bullish":
                    zl_macd > zl_macd_signal,

                "zl_macd_above_zero":
                    zl_macd > 0,

                "zl_macd_strength": 0.10,

                # ==================================================
                # RELATIVE VOLUME
                # ==================================================

                "relative_volume_at_time":
                    relative_volume_at_time,

                # ==================================================
                # CANDLE
                # ==================================================

                "candle_range": 1.00,
                "candle_body": 0.70,
                "candle_body_pct": candle_body_pct,

                "candle_upper_wick": 0.10,
                "candle_lower_wick": 0.20,

                "candle_bullish":
                    candle_bullish,

                "candle_close_position":
                    candle_close_position,

                # ==================================================
                # BREAKOUT
                # ==================================================

                "previous_high": 100.50,
                "previous_low": 99.50,

                "highest_10": 100.20,
                "lowest_10": 98.00,

                "breakout_above_10":
                    breakout_above_10,

                "breakdown_below_10": False,
            }
        )

    previous = rows[-2]
    current = rows[-1]

    # ============================================================
    # LEGACY MACD CROSS
    # ============================================================

    if macd_cross:

        previous["macd"] = 0.09
        previous["macd_signal"] = 0.10

        current["macd"] = 0.11
        current["macd_signal"] = 0.10

    else:

        previous["macd"] = 0.20
        previous["macd_signal"] = 0.10

        current["macd"] = 0.21
        current["macd_signal"] = 0.10

    # ============================================================
    # LEGACY EMA CROSS
    # ============================================================

    if ema_cross:

        previous["ema_9"] = 99.50
        previous["ema_21"] = 100.00

        current["ema_9"] = 100.30
        current["ema_21"] = 100.00

    else:

        previous["ema_9"] = 100.10
        previous["ema_21"] = 100.00

        current["ema_9"] = 100.30
        current["ema_21"] = 100.00

    current["ema_gap_pct"] = ema_gap_pct

    current["macd_histogram"] = (
        current["macd"]
        - current["macd_signal"]
    )

    # ============================================================
    # EMA 5 / 7
    # ============================================================

    if ema_5_7_bullish:

        current["ema_5"] = 100.50
        current["ema_7"] = 100.00

        previous["ema_5"] = 99.90
        previous["ema_7"] = 100.00

    else:

        current["ema_5"] = 99.90
        current["ema_7"] = 100.00

    return pd.DataFrame(rows)


# ============================================================
# BASIC VALIDATION
# ============================================================


def test_production_signal_engine_returns_signal_result():

    engine = SignalEngine(FakeSettings())

    result = engine.evaluate(
        "AAPL",
        make_dataframe(),
    )

    assert isinstance(
        result,
        SignalResult,
    )

    assert result.symbol == "AAPL"

    assert (
        0
        <= result.score
        <= 100
    )


def test_insufficient_data_is_rejected():

    engine = SignalEngine(FakeSettings())

    result = engine.evaluate(
        "AAPL",
        make_dataframe().iloc[:29],
    )

    assert (
        result.signal
        is Signal.REJECT
    )

    assert result.score == 0


def test_missing_indicator_is_rejected():

    engine = SignalEngine(FakeSettings())

    df = make_dataframe().drop(
        columns=["rsi"]
    )

    result = engine.evaluate(
        "AAPL",
        df,
    )

    assert (
        result.signal
        is Signal.REJECT
    )

    assert result.score == 0


# ============================================================
# BUY / FILTERS
# ============================================================


def test_bullish_setup_is_buy():

    engine = SignalEngine(
        FakeSettings()
    )

    result = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.003,
            macd_strength=0.40,
            ema_gap_pct=0.005,
            rsi=64.0,
            volume_ratio=1.5,
        ),
    )

    assert (
        result.signal
        is Signal.BUY
    )

    assert result.score >= 75


def test_bear_regime_blocks_long_entry():

    engine = SignalEngine(
        FakeSettings()
    )

    result = engine.evaluate(
        "AAPL",
        make_dataframe(),
        market_regime="BEAR",
    )

    assert (
        result.signal
        is Signal.REJECT
    )

    assert result.regime == "BEAR"


def test_rsi_out_of_bounds_blocks_buy():

    engine = SignalEngine(
        FakeSettings()
    )

    result = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.005,
            macd_strength=0.50,
            ema_gap_pct=0.005,
            rsi=75.0,
            volume_ratio=1.5,
        ),
    )

    assert (
        result.signal
        is Signal.REJECT
    )

    assert result.score >= 75


def test_volume_out_of_bounds_blocks_buy():

    engine = SignalEngine(
        FakeSettings()
    )

    result = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.005,
            macd_strength=0.50,
            ema_gap_pct=0.005,
            rsi=64.0,
            volume_ratio=0.5,
        ),
    )

    assert (
        result.signal
        is Signal.REJECT
    )


def test_no_crossover_trigger_blocks_buy():

    engine = SignalEngine(
        FakeSettings()
    )

    result = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.005,
            macd_strength=0.50,
            ema_gap_pct=0.005,
            rsi=64.0,
            volume_ratio=1.5,
            macd_cross=False,
            ema_cross=False,
        ),
    )

    assert (
        result.signal
        is Signal.REJECT
    )

    assert result.score < 75


# ============================================================
# V3 TREND
# ============================================================


def test_ema_5_7_bullish_setup():

    df = make_dataframe(
        ema_5_7_bullish=True,
    )

    last = df.iloc[-1]

    assert (
        last["ema_5"]
        > last["ema_7"]
    )

    assert (
        last["ema_5_slope"]
        > 0
    )

    assert (
        last["ema_7_slope"]
        > 0
    )


def test_bearish_ema_5_7_setup_is_detectable():

    df = make_dataframe(
        ema_5_7_bullish=False,
    )

    last = df.iloc[-1]

    assert (
        last["ema_5"]
        < last["ema_7"]
    )


def test_sma20_bullish_trend():

    df = make_dataframe(
        sma_20_slope=0.10,
        price_vs_sma20=0.003,
    )

    last = df.iloc[-1]

    assert (
        last["sma_20_slope"]
        > 0
    )

    assert (
        last["price_vs_sma20"]
        > 0
    )


# ============================================================
# V3 MOMENTUM
# ============================================================


def test_zero_lag_macd_bullish():

    df = make_dataframe(
        zl_macd=0.20,
        zl_macd_signal=0.10,
        zl_macd_histogram=0.10,
    )

    last = df.iloc[-1]

    assert (
        last["zl_macd"]
        > last["zl_macd_signal"]
    )

    assert (
        last["zl_macd_histogram"]
        > 0
    )

    assert (
        last["zl_macd_slope"]
        > 0
    )


def test_zero_lag_macd_bearish_is_detectable():

    df = make_dataframe(
        zl_macd=-0.10,
        zl_macd_signal=0.05,
        zl_macd_histogram=-0.15,
    )

    last = df.iloc[-1]

    assert (
        last["zl_macd"]
        < last["zl_macd_signal"]
    )

    assert (
        last["zl_macd_histogram"]
        < 0
    )


# ============================================================
# ICHIMOKU / CHIKOU
# ============================================================


def test_ichimoku_bullish_confirmation():

    df = make_dataframe(
        ichimoku_cloud_bullish=True,
        ichimoku_price_above_cloud=True,
        ichimoku_tenkan_above_kijun=True,
        chikou_bullish=True,
    )

    last = df.iloc[-1]

    assert (
        bool(last["ichimoku_cloud_bullish"])
    )

    assert (
        bool(last["ichimoku_price_above_cloud"])
    )

    assert (
        bool(last["ichimoku_tenkan_above_kijun"])
    )

    assert (
        bool(last["chikou_bullish"])
    )


def test_ichimoku_bearish_confirmation_is_detectable():

    df = make_dataframe(
        ichimoku_cloud_bullish=False,
        ichimoku_price_above_cloud=False,
        ichimoku_tenkan_above_kijun=False,
        chikou_bullish=False,
    )

    last = df.iloc[-1]

    assert not bool(
        last["ichimoku_cloud_bullish"]
    )

    assert not bool(
        last["ichimoku_price_above_cloud"]
    )

    assert not bool(
        last["chikou_bullish"]
    )


# ============================================================
# ADX / DMI
# ============================================================


def test_adx_dmi_bullish_confirmation():

    df = make_dataframe(
        adx=25.0,
        adx_slope=0.50,
        di_plus=30.0,
        di_minus=20.0,
        dmi_bullish=True,
    )

    last = df.iloc[-1]

    assert last["adx"] >= 20
    assert last["di_plus"] > last["di_minus"]
    assert bool(last["dmi_bullish"])


# ============================================================
# OBV / CMF
# ============================================================


def test_money_flow_is_bullish():

    df = make_dataframe(
        obv_slope=100.0,
        obv_bullish=True,
        cmf=0.10,
        cmf_slope=0.01,
        cmf_bullish=True,
    )

    last = df.iloc[-1]

    assert last["obv_slope"] > 0
    assert bool(last["obv_bullish"])

    assert last["cmf"] > 0
    assert last["cmf_slope"] > 0
    assert bool(last["cmf_bullish"])


# ============================================================
# VOLUME / VOLATILITY
# ============================================================


def test_relative_volume_is_healthy():

    df = make_dataframe(
        volume_ratio=1.5,
        relative_volume_at_time=1.5,
    )

    last = df.iloc[-1]

    assert (
        1.0
        <= last["volume_ratio"]
        <= 2.5
    )

    assert (
        last["relative_volume_at_time"]
        > 1.0
    )


def test_atr_volatility_is_positive():

    df = make_dataframe(
        atr_pct=0.01,
    )

    last = df.iloc[-1]

    assert (
        last["atr_pct"]
        > 0
    )


# ============================================================
# CANDLE CONFIRMATION
# ============================================================


def test_bullish_candle_confirmation():

    df = make_dataframe(
        candle_bullish=True,
        candle_body_pct=0.70,
        candle_close_position=0.80,
    )

    last = df.iloc[-1]

    assert bool(
        last["candle_bullish"]
    )

    assert (
        last["candle_body_pct"]
        >= 0.50
    )

    assert (
        last["candle_close_position"]
        >= 0.70
    )


# ============================================================
# BREAKOUT
# ============================================================


def test_breakout_confirmation():

    df = make_dataframe(
        breakout_above_10=True,
    )

    last = df.iloc[-1]

    assert bool(
        last["breakout_above_10"]
    )


# ============================================================
# SCORE DISTRIBUTION
# ============================================================


def test_stronger_setup_gets_higher_technical_score():

    engine = SignalEngine(
        FakeSettings()
    )

    moderate = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.002,
            macd_strength=0.25,
            ema_gap_pct=0.003,
            rsi=60.0,
            volume_ratio=1.5,
        ),
    )

    strong = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.003,
            macd_strength=0.40,
            ema_gap_pct=0.005,
            rsi=64.0,
            volume_ratio=1.5,
        ),
    )

    assert (
        moderate.signal
        is Signal.BUY
    )

    assert (
        strong.signal
        is Signal.BUY
    )

    assert (
        strong.score
        > moderate.score
    )


def test_reasonable_score_variation_does_not_collapse_to_same_cap():

    engine = SignalEngine(
        FakeSettings()
    )

    setup_a = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.002,
            macd_strength=0.25,
            ema_gap_pct=0.003,
            rsi=60.0,
            volume_ratio=1.5,
        ),
    )

    setup_b = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.003,
            macd_strength=0.40,
            ema_gap_pct=0.005,
            rsi=64.0,
            volume_ratio=1.5,
        ),
    )

    assert setup_a.score < 100
    assert setup_b.score < 100
    assert setup_b.score > setup_a.score


def test_maximum_technical_score_is_exactly_100():

    engine = SignalEngine(
        FakeSettings()
    )

    result = engine.evaluate(
        "AAPL",
        make_dataframe(
            price_vs_vwap=0.005,
            macd_strength=0.50,
            ema_gap_pct=0.005,
            rsi=64.0,
            volume_ratio=1.5,
            macd_cross=True,
            ema_cross=True,
        ),
    )

    assert (
        result.signal
        is Signal.BUY
    )

    assert result.score == 100


def test_market_regime_does_not_change_technical_score():

    engine = SignalEngine(
        FakeSettings()
    )

    df = make_dataframe(
        price_vs_vwap=0.003,
        macd_strength=0.40,
        ema_gap_pct=0.005,
        rsi=64.0,
        volume_ratio=1.5,
    )

    bullish_regime = engine.evaluate(
        "AAPL",
        df,
        market_regime="BULL",
    )

    sideways_regime = engine.evaluate(
        "AAPL",
        df,
        market_regime="SIDEWAYS",
    )

    assert (
        bullish_regime.score
        == sideways_regime.score
    )

    assert (
        bullish_regime.score
        == 94
    )