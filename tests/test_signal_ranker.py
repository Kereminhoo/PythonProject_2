

from strategy.signal_engine import Signal, SignalResult
from strategy.signal_ranker import SignalRanker


class FakeSettings:
    minimum_buy_score = 75


def create_signal(symbol, score):
    return SignalResult(
        symbol=symbol,
        signal=Signal.BUY,
        score=score,
        reasons=[],
    )


# ============================================================
# TEST 1
# ============================================================

def test_rank_sorts_by_score_descending():

    ranker = SignalRanker(
        FakeSettings()
    )

    signals = [
        create_signal("AAPL", 80),
        create_signal("TSLA", 95),
        create_signal("META", 88),
    ]

    ranked = ranker.rank(signals)

    assert [signal.symbol for signal in ranked] == [
        "TSLA",
        "META",
        "AAPL",
    ]


# ============================================================
# TEST 2
# ============================================================

def test_rank_keeps_score_values():

    ranker = SignalRanker(
        FakeSettings()
    )

    signals = [
        create_signal("AAPL", 80),
        create_signal("TSLA", 95),
    ]

    ranked = ranker.rank(signals)

    assert ranked[0].score == 95
    assert ranked[1].score == 80


# ============================================================
# TEST 3
# ============================================================

def test_rank_empty_list():

    ranker = SignalRanker(
        FakeSettings()
    )

    ranked = ranker.rank([])

    assert ranked == []


# ============================================================
# TEST 4
# ============================================================

def test_rank_does_not_modify_original_list():

    ranker = SignalRanker(
        FakeSettings()
    )

    signals = [
        create_signal("AAPL", 80),
        create_signal("TSLA", 95),
        create_signal("META", 88),
    ]

    original_symbols = [
        signal.symbol
        for signal in signals
    ]

    ranker.rank(signals)

    assert [
        signal.symbol
        for signal in signals
    ] == original_symbols


# ============================================================
# TEST 5
# ============================================================

def test_rank_tie_is_deterministic():

    ranker = SignalRanker(
        FakeSettings()
    )

    signals = [
        create_signal("TSLA", 90),
        create_signal("AAPL", 90),
        create_signal("META", 90),
    ]

    ranked = ranker.rank(signals)

    assert [signal.symbol for signal in ranked] == [
        "TSLA",
        "META",
        "AAPL",
    ]