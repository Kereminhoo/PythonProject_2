import pandas as pd

from backtest.engine import (
    BacktestEngine,
    BacktestConfig,
)

class FakeSettings:
    universe = (
        "AAPL",
        "NVDA",
        "SPY",
    )

    # Risk
    max_risk_per_trade_pct = 0.005
    max_daily_loss_pct = 0.01
    max_total_open_risk_pct = 0.01

    # Position limits
    max_open_positions = 1
    max_position_pct = 0.25
    max_position_size_pct = 0.25

    # ATR / Risk Reward
    atr_stop_multiplier = 1.5
    risk_reward_ratio = 2.0

    # Strategy
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

    volume_sma_period = 10

    timeframe_minutes = 5

    # Signal
    minimum_buy_score = 70

    # Cooldown
    cooldown_bars = 0

    # Daily targets
    daily_tp1_pct = 0.005
    daily_tp2_pct = 0.010


class RiskIntegrationSettings(FakeSettings):
    """
    Total open risk testinde ikinci pozisyonun
    max_open_positions kontrolüne takılmaması için
    pozisyon sayısını 2'ye çıkarır.
    """
    max_open_positions = 2


def create_test_data():
    timestamps = pd.date_range(
        "2026-01-01 14:30:00",
        periods=80,
        freq="5min",
    )

    rows = []
    price = 100.0

    for timestamp in timestamps:
        price += 0.10

        rows.append(
            {
                "symbol": "AAPL",
                "timestamp": timestamp,
                "open": price,
                "high": price + 0.20,
                "low": price - 0.10,
                "close": price + 0.05,
                "volume": 1000,
                "trade_count": 100,
                "vwap": price,
            }
        )

    df = pd.DataFrame(rows)

    df = df.set_index(
        ["symbol", "timestamp"]
    )

    return df


def create_engine():
    settings = FakeSettings()

    return BacktestEngine(
        settings=settings,
        config=BacktestConfig(
            initial_capital=100.0,
        ),
    )


def test_backtest_engine_initializes():
    engine = create_engine()

    assert engine.portfolio.initial_capital == 100.0
    assert engine.portfolio.cash == 100.0
    assert len(engine.portfolio.positions) == 0


def test_prepare_data():
    engine = create_engine()

    df = create_test_data()

    prepared = engine.prepare_data(df)

    assert "AAPL" in prepared

    symbol_df = prepared["AAPL"]

    assert len(symbol_df) == 80

    assert "macd" in symbol_df.columns
    assert "rsi" in symbol_df.columns
    assert "ema_9" in symbol_df.columns
    assert "ema_21" in symbol_df.columns
    assert "atr" in symbol_df.columns
    assert "volume_ratio" in symbol_df.columns


def test_build_timeline():
    engine = create_engine()

    df = create_test_data()

    prepared = engine.prepare_data(df)

    timeline = engine.build_timeline(
        prepared
    )

    assert len(timeline) == 80
    assert timeline == sorted(timeline)


def test_backtest_runs():
    engine = create_engine()

    df = create_test_data()

    result = engine.run(df)

    assert result is not None

    assert engine.portfolio.cash > 0

    assert len(
        engine.portfolio.equity_curve
    ) > 0


def test_backtest_has_central_position_sizer():
    engine = create_engine()

    assert engine.position_sizer is not None


def test_backtest_has_central_risk_manager():
    engine = create_engine()

    assert engine.risk_manager is not None


def test_backtest_risk_registry_starts_empty():
    engine = create_engine()

    total_open_risk = (
        engine.risk_manager.calculate_total_open_risk()
    )

    assert total_open_risk == 0.0


def test_backtest_risk_registry_registers_and_unregisters():
    engine = create_engine()

    engine.register_position_risk(
        symbol="AAPL",
        quantity=1,
        entry_price=100.0,
        stop_price=99.0,
    )

    total_open_risk = (
        engine.risk_manager.calculate_total_open_risk()
    )

    assert total_open_risk == 1.0

    engine.unregister_position_risk(
        "AAPL"
    )

    assert (
        engine.risk_manager.calculate_total_open_risk()
        == 0.0
    )


def test_backtest_rejects_trade_when_total_open_risk_is_exceeded():
    settings = RiskIntegrationSettings()

    engine = BacktestEngine(
        settings=settings,
        config=BacktestConfig(
            initial_capital=100.0,
        ),
    )

    # İlk açık pozisyon:
    # 1 adet x (100 - 99) = $1 risk
    engine.register_position_risk(
        symbol="AAPL",
        quantity=1,
        entry_price=100.0,
        stop_price=99.0,
    )

    risk_decision = (
        engine.risk_manager.approve_position(
            symbol="NVDA",
            quantity=1,
            entry_price=100.0,
            stop_price=99.0,
            equity=100.0,
            daily_pnl_pct=0.0,
        )
    )

    assert risk_decision.approved is False

    assert (
        risk_decision.projected_open_risk
        == 2.0
    )

    assert (
        risk_decision.max_total_open_risk
        == 1.0
    )


def test_backtest_run_resets_state():
    engine = create_engine()

    df = create_test_data()

    first_result = engine.run(df)

    first_equity = (
        engine.portfolio.calculate_equity({})
    )

    first_trade_attempts = (
        engine.trade_attempt_count
    )

    first_total_risk = (
        engine.risk_manager.calculate_total_open_risk()
    )

    second_result = engine.run(df)

    second_equity = (
        engine.portfolio.calculate_equity({})
    )

    second_trade_attempts = (
        engine.trade_attempt_count
    )

    second_total_risk = (
        engine.risk_manager.calculate_total_open_risk()
    )

    assert second_result == first_result

    assert second_equity == first_equity

    assert (
        second_trade_attempts
        == first_trade_attempts
    )

    assert first_total_risk == 0.0
    assert second_total_risk == 0.0

    assert (
        engine.portfolio.initial_capital
        == 100.0
    )

    assert (
        engine.portfolio.cash
        <= 100.0
    )