from typing import Iterable

from strategy.signal_engine import SignalResult


class SignalRanker:
    """
    BUY sinyallerini score değerine göre sıralar.

    Amaç:
    - Aynı zaman dilimindeki BUY adaylarını toplamak
    - En yüksek kaliteli fırsatları öne çıkarmak
    - BacktestEngine'in universe sırasına bağımlılığını kaldırmak

    Not:
    SignalRanker sadece sıralama yapar.
    Risk yönetimi ve pozisyon açma kararı burada verilmez.
    """

    def __init__(self, settings):
        self.settings = settings

    def rank(
        self,
        signals: Iterable[SignalResult],
    ) -> list[SignalResult]:
        """
        SignalResult listesini score'a göre büyükten küçüğe sıralar.

        Örnek:

            AAPL 80
            TSLA 95
            META 88

        sonuç:

            TSLA 95
            META 88
            AAPL 80
        """

        signal_list = list(signals)

        if not signal_list:
            return []

        ranked = sorted(
            signal_list,
            key=lambda signal: (
                signal.score,
                signal.symbol,
            ),
            reverse=True,
        )

        return ranked