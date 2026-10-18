from types import SimpleNamespace

from backtest.portfolio import Portfolio


def create_portfolio():
    return Portfolio(
        initial_capital=1000.0,
        cash=1000.0,
    )


def open_test_position():
    portfolio = create_portfolio()

    portfolio.open_position(
        symbol="AAPL",
        quantity=1.0,
        entry_price=100.0,
        stop_price=98.0,
        target_price=None,
        entry_time=None,
    )

    return portfolio


# ============================================================
# TEST 1
# INITIAL POSITION STATE
# ============================================================

def test_initial_trailing_state():

    portfolio = open_test_position()

    position = portfolio.positions["AAPL"]

    assert position.entry_price == 100.0

    assert position.stop_price == 98.0

    assert position.initial_stop_price == 98.0

    assert position.highest_price == 100.0

    assert position.current_r == 0.0

    assert position.stop_r == -1.0

    assert position.trailing_active is False

    assert position.stop_update_count == 0


# ============================================================
# TEST 2
# POSITION STATE UPDATE
# ============================================================

def test_position_state_updates_highest_price_and_r():

    portfolio = open_test_position()

    position = portfolio.update_position_state(
        symbol="AAPL",
        current_price=102.0,
    )

    assert position is not None

    assert position.highest_price == 102.0

    # Initial risk = 100 - 98 = 2
    # Profit = 102 - 100 = 2
    # Current R = +1
    assert position.current_r == 1.0


# ============================================================
# TEST 3
# STOP CANNOT MOVE BACKWARDS
# ============================================================

def test_stop_cannot_move_backwards():

    portfolio = open_test_position()

    updated = portfolio.update_stop_price(
        symbol="AAPL",
        new_stop_price=97.0,
    )

    assert updated is False

    position = portfolio.positions["AAPL"]

    assert position.stop_price == 98.0

    assert position.stop_update_count == 0


# ============================================================
# TEST 4
# STOP CAN MOVE TO BREAK EVEN
# ============================================================

def test_stop_can_move_to_break_even():

    portfolio = open_test_position()

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=102.0,
    )

    updated = portfolio.update_stop_price(
        symbol="AAPL",
        new_stop_price=100.0,
    )

    assert updated is True

    position = portfolio.positions["AAPL"]

    assert position.stop_price == 100.0

    assert position.stop_update_count == 1

    assert position.trailing_active is True

    assert position.stop_r == 0.0


# ============================================================
# TEST 5
# PROFIT LOCK
# ============================================================

def test_stop_can_lock_profit():

    portfolio = open_test_position()

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=103.0,
    )

    updated = portfolio.update_stop_price(
        symbol="AAPL",
        new_stop_price=101.0,
    )

    assert updated is True

    position = portfolio.positions["AAPL"]

    assert position.stop_price == 101.0

    # Initial risk = 2
    # Locked profit = +1
    # 1 / 2 = +0.5R
    assert position.stop_r == 0.5


# ============================================================
# TEST 6
# STOP CANNOT BE SET ABOVE HIGHEST PRICE
# ============================================================

def test_stop_cannot_be_above_reference_price():

    portfolio = open_test_position()

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=105.0,
    )

    updated = portfolio.update_stop_price(
        symbol="AAPL",
        new_stop_price=105.0,
    )

    assert updated is False

    position = portfolio.positions["AAPL"]

    assert position.stop_price == 98.0


# ============================================================
# TEST 7
# CURRENT R CAN BE NEGATIVE
# ============================================================

def test_current_r_can_be_negative():

    portfolio = open_test_position()

    position = portfolio.update_position_state(
        symbol="AAPL",
        current_price=99.0,
    )

    assert position.current_r == -0.5


# ============================================================
# TEST 8
# HIGHEST PRICE NEVER MOVES BACK
# ============================================================

def test_highest_price_only_moves_up():

    portfolio = open_test_position()

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=105.0,
    )

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=102.0,
    )

    position = portfolio.positions["AAPL"]

    assert position.highest_price == 105.0


# ============================================================
# TEST 9
# MULTIPLE STOP UPDATES
# ============================================================

def test_multiple_stop_updates():

    portfolio = open_test_position()

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=102.0,
    )

    assert (
        portfolio.update_stop_price(
            symbol="AAPL",
            new_stop_price=100.0,
        )
        is True
    )

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=103.0,
    )

    assert (
        portfolio.update_stop_price(
            symbol="AAPL",
            new_stop_price=101.0,
        )
        is True
    )

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=106.0,
    )

    assert (
        portfolio.update_stop_price(
            symbol="AAPL",
            new_stop_price=104.0,
        )
        is True
    )

    position = portfolio.positions["AAPL"]

    assert position.stop_price == 104.0

    assert position.stop_update_count == 3

    assert position.trailing_active is True

    assert position.highest_price == 106.0


# ============================================================
# TEST 10
# CLOSED TRADE STORES TRAILING METADATA
# ============================================================

def test_closed_trade_stores_trailing_metadata():

    portfolio = open_test_position()

    portfolio.update_position_state(
        symbol="AAPL",
        current_price=104.0,
    )

    portfolio.update_stop_price(
        symbol="AAPL",
        new_stop_price=102.0,
    )

    trade = portfolio.close_position(
        symbol="AAPL",
        exit_price=103.0,
        exit_time=None,
        exit_reason="STOP",
    )

    assert trade.entry_metrics[
        "initial_stop_price"
    ] == 98.0

    assert trade.entry_metrics[
        "final_stop_price"
    ] == 102.0

    assert trade.entry_metrics[
        "highest_price"
    ] == 104.0

    assert trade.entry_metrics[
        "stop_update_count"
    ] == 1

    assert trade.entry_metrics[
        "trailing_active"
    ] is True