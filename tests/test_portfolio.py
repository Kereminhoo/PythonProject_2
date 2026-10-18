from backtest.portfolio import Portfolio


def test_open_position_reduces_cash():

    portfolio = Portfolio(

        initial_capital=100.0,

        cash=100.0
    )

    portfolio.open_position(

        symbol="AAPL",

        quantity=0.25,

        entry_price=100.0,

        stop_price=99.50,

        target_price=100.50,

        entry_time="TEST"
    )

    assert portfolio.cash == 75.0

    assert "AAPL" in portfolio.positions


def test_close_position_creates_profit():

    portfolio = Portfolio(

        initial_capital=100.0,

        cash=100.0
    )

    portfolio.open_position(

        symbol="AAPL",

        quantity=0.25,

        entry_price=100.0,

        stop_price=99.50,

        target_price=100.50,

        entry_time="ENTRY"
    )

    trade = portfolio.close_position(

        symbol="AAPL",

        exit_price=100.50,

        exit_time="EXIT",

        exit_reason="TARGET"
    )

    assert trade.pnl == 0.125

    assert trade.pnl_pct == 0.005

    assert portfolio.cash == 100.125

    assert len(
        portfolio.closed_trades
    ) == 1

    assert (
        "AAPL"
        not in portfolio.positions
    )


def test_stop_loss_creates_loss():

    portfolio = Portfolio(

        initial_capital=100.0,

        cash=100.0
    )

    portfolio.open_position(

        symbol="AAPL",

        quantity=0.25,

        entry_price=100.0,

        stop_price=99.50,

        target_price=100.50,

        entry_time="ENTRY"
    )

    trade = portfolio.close_position(

        symbol="AAPL",

        exit_price=99.50,

        exit_time="STOP",

        exit_reason="STOP"
    )

    assert trade.pnl == -0.125

    assert trade.pnl_pct == -0.005

    assert portfolio.cash == 99.875


def test_equity_includes_open_position():

    portfolio = Portfolio(

        initial_capital=100.0,

        cash=100.0
    )

    portfolio.open_position(

        symbol="AAPL",

        quantity=0.25,

        entry_price=100.0,

        stop_price=99.50,

        target_price=100.50,

        entry_time="ENTRY"
    )

    equity = portfolio.calculate_equity({

        "AAPL": 101.0
    })

    assert equity == 100.25


def test_unrealized_pnl():

    portfolio = Portfolio(

        initial_capital=100.0,

        cash=100.0
    )

    portfolio.open_position(

        symbol="AAPL",

        quantity=0.25,

        entry_price=100.0,

        stop_price=99.50,

        target_price=100.50,

        entry_time="ENTRY"
    )

    portfolio.update_unrealized_pnl({

        "AAPL": 101.0
    })

    position = (
        portfolio.positions["AAPL"]
    )

    assert position.unrealized_pnl == 0.25
