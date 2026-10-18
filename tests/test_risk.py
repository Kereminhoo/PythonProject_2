from types import SimpleNamespace

from risk.risk_manager import RiskManager
from risk.position_sizer import PositionSizer


def create_settings():

    return SimpleNamespace(

        max_risk_per_trade_pct=0.005,

        max_total_open_risk_pct=0.01,

        max_daily_loss_pct=0.01,

        max_open_positions=4,

        micro_account_mode=False,

        micro_max_open_positions=1,

        max_position_pct=0.25,

        max_position_size_pct=0.25,

        atr_stop_multiplier=1.0,

        risk_reward_ratio=2.0
    )


def create_account(
    equity=100.0,
    last_equity=100.0
):

    return SimpleNamespace(

        equity=str(equity),

        last_equity=str(last_equity)
    )


class FakeTradingClient:

    def __init__(
        self,
        equity=100.0,
        last_equity=100.0,
        positions=None
    ):

        self.account = create_account(
            equity,
            last_equity
        )

        self.positions = (
            positions
            if positions is not None
            else []
        )

    def get_account(self):

        return self.account

    def get_all_positions(self):

        return self.positions


# ==================================================
# TEST 1
# MAX RISK AMOUNT
# ==================================================

def test_max_risk_amount():

    client = FakeTradingClient(
        equity=100.0
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    risk = manager.get_max_risk_amount()

    assert risk == 0.50


# ==================================================
# TEST 2
# POSITION SIZE
# ==================================================

def test_position_size_respects_risk():

    client = FakeTradingClient(
        equity=100.0
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    quantity = manager.calculate_position_size(

        equity=100.0,

        entry_price=100.0,

        stop_price=99.50
    )

    assert quantity == 1.0


# ==================================================
# TEST 3
# POSITION VALUE LIMIT
# ==================================================

def test_position_value_limit():

    client = FakeTradingClient(
        equity=100.0
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    quantity = manager.calculate_position_size(

        equity=100.0,

        entry_price=100.0,

        stop_price=99.50
    )

    limited_quantity = (
        manager.apply_position_value_limit(

            quantity=quantity,

            entry_price=100.0,

            equity=100.0
        )
    )

    assert limited_quantity == 0.25


# ==================================================
# TEST 4
# DAILY LOSS LIMIT
# ==================================================

def test_daily_loss_limit():

    client = FakeTradingClient(

        equity=99.0,

        last_equity=100.0
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    assert (
        manager.daily_loss_limit_reached()
        is True
    )


# ==================================================
# TEST 5
# DAILY LOSS BELOW LIMIT
# ==================================================

def test_daily_loss_below_limit():

    client = FakeTradingClient(

        equity=99.5,

        last_equity=100.0
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    assert (
        manager.daily_loss_limit_reached()
        is False
    )


# ==================================================
# TEST 6
# POSITION LIMIT
# ==================================================

def test_position_limit():

    positions = [

        SimpleNamespace(symbol="AAPL"),

        SimpleNamespace(symbol="MSFT"),

        SimpleNamespace(symbol="NVDA"),

        SimpleNamespace(symbol="SPY")
    ]

    client = FakeTradingClient(
        positions=positions
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    decision = manager.approve_trade(
        "TSLA"
    )

    assert decision.approved is False

    assert (
        "Maximum open positions"
        in decision.reason
    )


# ==================================================
# TEST 7A
# EFFECTIVE MICRO POSITION LIMIT
# ==================================================

def test_effective_micro_position_limit():

    positions = [
        SimpleNamespace(symbol="AAPL"),
    ]

    client = FakeTradingClient(
        positions=positions
    )

    settings = create_settings()
    settings.micro_account_mode = True

    manager = RiskManager(
        client,
        settings
    )

    assert manager.get_effective_max_open_positions() == 1

    decision = manager.approve_position(
        symbol="TSLA",
        quantity=0.5,
        entry_price=100.0,
        stop_price=99.0,
        equity=100.0,
        daily_pnl_pct=0.0,
    )

    assert decision.approved is False
    assert "Maximum open positions" in decision.reason


# ==================================================
# TEST 7
# DUPLICATE POSITION
# ==================================================

def test_duplicate_position():

    positions = [

        SimpleNamespace(
            symbol="AAPL"
        )
    ]

    client = FakeTradingClient(
        positions=positions
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    decision = manager.approve_trade(
        "AAPL"
    )

    assert decision.approved is False

    assert (
        "already exists"
        in decision.reason
    )


# ==================================================
# TEST 8
# APPROVED TRADE
# ==================================================

def test_trade_approved():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    decision = manager.approve_trade(
        "AAPL"
    )

    assert decision.approved is True

    assert (
        decision.max_risk_amount
        == 0.50
    )


# ==================================================
# TEST 9
# POSITION RISK REGISTRY
# ==================================================

def test_register_position_risk():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    manager.register_position_risk(

        symbol="AAPL",

        quantity=10,

        entry_price=100.0,

        stop_price=99.0
    )

    assert (
        manager.calculate_total_open_risk()
        == 10.0
    )


# ==================================================
# TEST 10
# TOTAL OPEN RISK
# ==================================================

def test_total_open_risk():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    manager.register_position_risk(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        stop_price=99.0
    )

    manager.register_position_risk(
        symbol="SPY",
        quantity=5,
        entry_price=100.0,
        stop_price=98.0
    )

    assert (
        manager.calculate_total_open_risk()
        == 20.0
    )


# ==================================================
# TEST 11
# TOTAL OPEN RISK PERCENT
# ==================================================

def test_total_open_risk_pct():

    client = FakeTradingClient(
        equity=100.0
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    manager.register_position_risk(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        stop_price=99.0
    )

    assert (
        manager.calculate_total_open_risk_pct()
        == 0.10
    )


# ==================================================
# TEST 12
# TOTAL RISK WITH NEW TRADE
# ==================================================

def test_total_risk_with_new_trade():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    manager.register_position_risk(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        stop_price=99.0
    )

    projected = (
        manager.calculate_total_risk_with_trade(

            quantity=5,

            entry_price=100.0,

            stop_price=98.0
        )
    )

    assert projected == 20.0


# ==================================================
# TEST 13
# TOTAL RISK LIMIT
# ==================================================

def test_total_open_risk_limit():

    client = FakeTradingClient(
        equity=100.0
    )

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    manager.register_position_risk(
        symbol="AAPL",
        quantity=0.5,
        entry_price=100.0,
        stop_price=99.0
    )

    assert (
        manager.total_open_risk_limit_reached(
            additional_risk=0.50,
            equity=100.0
        )
        is False
    )

    assert (
        manager.total_open_risk_limit_reached(
            additional_risk=0.51,
            equity=100.0
        )
        is True
    )


# ==================================================
# TEST 14
# UNREGISTER POSITION
# ==================================================

def test_unregister_position():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    manager.register_position_risk(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        stop_price=99.0
    )

    assert (
        manager.calculate_total_open_risk()
        == 10.0
    )

    manager.unregister_position(
        "AAPL"
    )

    assert (
        manager.calculate_total_open_risk()
        == 0.0
    )


# ==================================================
# TEST 18
# BREAK EVEN STOP
# ==================================================

def test_register_position_risk_allows_break_even_stop():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    manager.register_position_risk(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        stop_price=100.0
    )

    assert (
        manager.calculate_total_open_risk()
        == 0.0
    )


# ==================================================
# TEST 19
# PROFIT LOCK STOP
# ==================================================

def test_register_position_risk_allows_profit_locked_stop():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    manager.register_position_risk(
        symbol="AAPL",
        quantity=10,
        entry_price=100.0,
        stop_price=101.0
    )

    assert (
        manager.calculate_total_open_risk()
        == 0.0
    )


# ==================================================
# TEST 20
# NEW TRADE WITH LOCKED STOP IS INVALID
# ==================================================

def test_new_trade_risk_with_locked_stop_is_invalid():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    risk = manager.calculate_trade_risk(
        quantity=10,
        entry_price=100.0,
        stop_price=101.0,
    )

    assert risk == float("inf")


# ==================================================
# TEST 21
# NEW TRADE APPROVAL REJECTS LOCKED STOP
# ==================================================

def test_approve_position_rejects_locked_stop():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    decision = manager.approve_position(
        symbol="AAPL",
        quantity=1.0,
        entry_price=100.0,
        stop_price=100.0,
        equity=100.0,
        daily_pnl_pct=0.0,
    )

    assert decision.approved is False

    assert (
        "below entry price"
        in decision.reason
    )


# ==================================================
# TEST 22
# VALID NEW TRADE APPROVAL
# ==================================================

def test_approve_position_accepts_valid_stop():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    decision = manager.approve_position(
        symbol="AAPL",
        quantity=0.5,
        entry_price=100.0,
        stop_price=99.0,
        equity=100.0,
        daily_pnl_pct=0.0,
    )

    assert decision.approved is True
    assert decision.new_trade_risk == 0.5


# ==================================================
# TEST 23
# INVALID NEW TRADE QUANTITY IS REJECTED
# ==================================================

def test_approve_position_rejects_zero_quantity():

    client = FakeTradingClient()

    settings = create_settings()

    manager = RiskManager(
        client,
        settings
    )

    decision = manager.approve_position(
        symbol="AAPL",
        quantity=0.0,
        entry_price=100.0,
        stop_price=99.0,
        equity=100.0,
        daily_pnl_pct=0.0,
    )

    assert decision.approved is False
    assert "quantity" in decision.reason.lower()
