from config.settings import load_settings
from data.market_data import MarketData


def test_historical_data():

    settings = load_settings()

    market_data = MarketData(settings)

    df = market_data.get_historical_bars(
        "2025-01-02",
        "2025-01-10"
    )

    assert df is not None
    assert not df.empty

    assert "open" in df.columns
    assert "high" in df.columns
    assert "low" in df.columns
    assert "close" in df.columns
    assert "volume" in df.columns

    assert df.index.is_monotonic_increasing
