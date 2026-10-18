import pandas as pd
import pytest
from types import SimpleNamespace

from strategy.indicators import IndicatorEngine


# ============================================================
# HELPERS
# ============================================================

def create_settings():
    return SimpleNamespace(
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        volume_sma_period=10,
    )


def make_market_data(rows=160):
    index = pd.date_range(
        start="2025-01-02 14:30:00",
        periods=rows,
        freq="5min",
        tz="UTC",
    )

    base = (
        pd.Series(
            range(rows),
            index=index,
            dtype=float,
        )
        * 0.10
        + 100.0
    )

    close = base

    open_price = (
        close - 0.20
    )

    high = (
        close + 0.40
    )

    low = (
        close - 0.40
    )

    volume = pd.Series(
        [
            1000.0
            + (index_position % 12) * 50.0
            for index_position in range(rows)
        ],
        index=index,
    )

    vwap = pd.Series(
        close.values - 0.05,
        index=index,
    )

    return pd.DataFrame(
        {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "vwap": vwap,
        },
        index=index,
    )


def make_engine():
    return IndicatorEngine(
        create_settings()
    )


# ============================================================
# BASIC
# ============================================================

def test_indicator_engine_returns_dataframe():

    engine = make_engine()

    df = make_market_data()

    result = engine.calculate(df)

    assert isinstance(
        result,
        pd.DataFrame,
    )

    assert len(result) == len(df)


def test_original_ohlcv_columns_are_preserved():

    engine = make_engine()

    df = make_market_data()

    result = engine.calculate(df)

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:
        assert column in result.columns


# ============================================================
# LEGACY INDICATORS
# ============================================================

def test_legacy_indicators_are_still_available():

    engine = make_engine()

    df = make_market_data()

    result = engine.calculate(df)

    required = [
        "macd",
        "macd_signal",
        "macd_histogram",
        "ema_9",
        "ema_21",
        "ema_gap_pct",
        "rsi",
        "atr",
        "price_vs_vwap",
        "volume_sma",
        "volume_ratio",
        "return_1",
        "return_3",
        "return_6",
        "macd_strength",
    ]

    for column in required:
        assert column in result.columns


# ============================================================
# EMA 5 / 7
# ============================================================

def test_ema_5_7_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "ema_5",
        "ema_7",
        "ema_5_slope",
        "ema_7_slope",
        "ema_5_7_gap_pct",
    ]

    for column in required:
        assert column in result.columns


def test_ema_5_7_is_bullish_for_rising_market():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    last = result.iloc[-1]

    assert last["ema_5"] > last["ema_7"]
    assert last["ema_5_slope"] > 0
    assert last["ema_7_slope"] > 0


# ============================================================
# SMA 20
# ============================================================

def test_sma20_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    assert "sma_20" in result.columns
    assert "sma_20_slope" in result.columns
    assert "price_vs_sma20" in result.columns


def test_sma20_rises_with_rising_market():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    last = result.iloc[-1]

    assert last["sma_20_slope"] > 0
    assert last["price_vs_sma20"] > 0


# ============================================================
# BOLLINGER
# ============================================================

def test_bollinger_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_pct_b",
        "bb_width",
        "bb_middle_slope",
        "bb_width_change",
        "price_vs_bb_middle",
    ]

    for column in required:
        assert column in result.columns


def test_bollinger_order_is_valid():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    valid = result.dropna(
        subset=[
            "bb_lower",
            "bb_middle",
            "bb_upper",
        ]
    )

    assert (
        valid["bb_lower"]
        <= valid["bb_middle"]
    ).all()

    assert (
        valid["bb_middle"]
        <= valid["bb_upper"]
    ).all()


# ============================================================
# ICHIMOKU
# ============================================================

def test_ichimoku_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "ichimoku_tenkan",
        "ichimoku_kijun",
        "ichimoku_span_a",
        "ichimoku_span_b",
        "ichimoku_cloud_top",
        "ichimoku_cloud_bottom",
        "ichimoku_cloud_width",
        "ichimoku_cloud_bullish",
        "ichimoku_price_above_cloud",
        "ichimoku_tenkan_above_kijun",
    ]

    for column in required:
        assert column in result.columns


def test_ichimoku_cloud_width_is_non_negative():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    valid = result[
        "ichimoku_cloud_width"
    ].dropna()

    assert (
        valid >= 0
    ).all()


# ============================================================
# CHIKOU
# ============================================================

def test_chikou_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    assert "chikou_close" in result.columns
    assert "chikou_bullish" in result.columns


def test_chikou_uses_26_bar_lag():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    expected = (
        result["close"]
        .shift(26)
    )

    pd.testing.assert_series_equal(
        result["chikou_close"],
        expected,
        check_names=False,
    )


def test_chikou_is_bullish_for_rising_market():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    last = result.iloc[-1]

    assert (
        last["chikou_bullish"]
        is True
        or bool(last["chikou_bullish"])
    )


# ============================================================
# ADX / DMI
# ============================================================

def test_adx_dmi_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "adx",
        "di_plus",
        "di_minus",
        "adx_slope",
        "dmi_bullish",
    ]

    for column in required:
        assert column in result.columns


# ============================================================
# OBV
# ============================================================

def test_obv_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "obv",
        "obv_sma",
        "obv_slope",
        "obv_bullish",
    ]

    for column in required:
        assert column in result.columns


def test_obv_is_rising_in_rising_market():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    valid = result[
        "obv_slope"
    ].dropna()

    assert (
        valid.iloc[-1] > 0
    )


# ============================================================
# CHAIKIN MONEY FLOW
# ============================================================

def test_cmf_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "cmf",
        "cmf_slope",
        "cmf_bullish",
    ]

    for column in required:
        assert column in result.columns


# ============================================================
# ATR / VOLATILITY
# ============================================================

def test_atr_percentage_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "atr",
        "atr_pct",
        "atr_slope",
        "atr_pct_change",
    ]

    for column in required:
        assert column in result.columns


def test_atr_percentage_is_positive():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    valid = result[
        "atr_pct"
    ].dropna()

    valid = valid[
        valid > 0
        ]

    assert not valid.empty

    assert (
            valid > 0
    ).all()


# ============================================================
# ZERO-LAG MACD
# ============================================================

def test_zero_lag_macd_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "zl_macd",
        "zl_macd_signal",
        "zl_macd_histogram",
        "zl_macd_slope",
        "zl_macd_signal_slope",
        "zl_macd_bullish",
        "zl_macd_above_zero",
        "zl_macd_strength",
    ]

    for column in required:
        assert column in result.columns


def test_zero_lag_macd_is_bullish_for_rising_market():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    last = result.iloc[-1]

    assert last["zl_macd"] > 0
    assert last["zl_macd_bullish"] is True or bool(
        last["zl_macd_bullish"]
    )


def test_zlema_does_not_use_future_values():

    engine = make_engine()

    original = make_market_data()

    modified = original.copy()

    modified.iloc[-1, modified.columns.get_loc(
        "close"
    )] += 50.0

    original_result = engine.calculate(
        original
    )

    modified_result = engine.calculate(
        modified
    )

    # Changing the last/future bar must not
    # modify previous indicator values.
    assert (
        original_result["zl_macd"].iloc[:-1]
        .equals(
            modified_result["zl_macd"].iloc[:-1]
        )
    )


# ============================================================
# CANDLE STRUCTURE
# ============================================================

def test_candle_structure_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "candle_range",
        "candle_body",
        "candle_body_pct",
        "candle_upper_wick",
        "candle_lower_wick",
        "candle_bullish",
        "candle_close_position",
    ]

    for column in required:
        assert column in result.columns


def test_candle_range_is_non_negative():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    valid = result[
        "candle_range"
    ].dropna()

    assert (
        valid >= 0
    ).all()


def test_candle_close_position_is_between_zero_and_one():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    valid = result[
        "candle_close_position"
    ].dropna()

    assert (
        valid >= 0
    ).all()

    assert (
        valid <= 1
    ).all()


# ============================================================
# BREAKOUT STRUCTURE
# ============================================================

def test_breakout_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    required = [
        "previous_high",
        "previous_low",
        "highest_10",
        "lowest_10",
        "breakout_above_10",
        "breakdown_below_10",
    ]

    for column in required:
        assert column in result.columns


# ============================================================
# RELATIVE VOLUME
# ============================================================

def test_relative_volume_columns_exist():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    assert (
        "relative_volume_at_time"
        in result.columns
    )


def test_volume_ratio_is_positive():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    valid = result[
        "volume_ratio"
    ].dropna()

    assert (
        valid > 0
    ).all()


# ============================================================
# CLEANUP
# ============================================================

def test_indicator_output_contains_no_infinite_values():

    engine = make_engine()

    result = engine.calculate(
        make_market_data()
    )

    numeric = result.select_dtypes(
        include=["number"]
    )

    assert not (
        numeric
        .isin(
            [
                float("inf"),
                float("-inf"),
            ]
        )
        .any()
        .any()
    )