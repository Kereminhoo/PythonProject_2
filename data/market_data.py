from datetime import datetime, timedelta, timezone
from typing import Iterable
import pandas as pd
from alpaca.data.historical import (
    StockHistoricalDataClient,
)
from alpaca.data.requests import (
    StockBarsRequest,
)
from alpaca.data.timeframe import (
    TimeFrame,
    TimeFrameUnit,
)

class MarketData:

    def __init__(self, settings):

        self.settings = settings

        self.client = (
            StockHistoricalDataClient(
                settings.alpaca_api_key,
                settings.alpaca_secret_key,
            )
        )

    # ==================================================
    # SYMBOL BATCHING
    # ==================================================

    def _symbol_batches(
        self,
        symbols: Iterable[str],
    ):

        symbols = tuple(
            symbols
        )

        batch_size = int(
            getattr(
                self.settings,
                "universe_batch_size",
                25,
            )
        )

        if batch_size <= 0:

            batch_size = 25

        for start in range(
            0,
            len(symbols),
            batch_size,
        ):

            yield symbols[
                start:start + batch_size
            ]

    # ==================================================
    # NORMALIZE
    # ==================================================

    @staticmethod
    def _normalize(df):

        if df is None or df.empty:

            return df

        if (
            isinstance(
                df.index,
                pd.MultiIndex,
            )
            and
            "symbol" in df.index.names
            and
            "timestamp" in df.index.names
        ):

            return df.sort_index()

        return df

    # ==================================================
    # TIMEFRAME
    # ==================================================

    def _timeframe(self):

        return TimeFrame(
            self.settings.timeframe_minutes,
            TimeFrameUnit.Minute,
        )

    # ==================================================
    # RECENT DATA
    # ==================================================

    def get_recent_bars(self):

        end_time = datetime.now(
            timezone.utc
        )

        start_time = (
            end_time
            - timedelta(days=5)
        )

        frames = []

        for symbols in self._symbol_batches(
            self.settings.universe
        ):

            request = StockBarsRequest(

                symbol_or_symbols=symbols,

                timeframe=self._timeframe(),

                start=start_time,

                end=end_time,
            )

            data = (
                self.client
                .get_stock_bars(request)
                .df
            )

            if data is not None and not data.empty:

                frames.append(data)

        if not frames:

            return pd.DataFrame()

        combined = pd.concat(
            frames
        )

        return self._normalize(
            combined
        )

    # ==================================================
    # HISTORICAL DATA
    # ==================================================

    def get_historical_bars(
        self,
        start_date: str,
        end_date: str,
    ):

        start_time = (
            datetime.fromisoformat(
                start_date
            )
            .replace(
                tzinfo=timezone.utc
            )
        )

        # Tarihin tamamını dahil et.
        #
        # Örnek:
        # "2025-01-31"
        #
        # -> 2025-01-31 23:59:59.999999 UTC

        end_time = (
            datetime.fromisoformat(
                end_date
            )
            .replace(
                tzinfo=timezone.utc
            )
            + timedelta(
                days=1
            )
            - timedelta(
                microseconds=1
            )
        )

        if end_time <= start_time:

            raise ValueError(
                "End date start date'den "
                "büyük olmalıdır."
            )

        frames = []

        for symbols in self._symbol_batches(
            self.settings.universe
        ):

            request = StockBarsRequest(

                symbol_or_symbols=symbols,

                timeframe=self._timeframe(),

                start=start_time,

                end=end_time,
            )

            data = (
                self.client
                .get_stock_bars(request)
                .df
            )

            if data is not None and not data.empty:

                frames.append(data)

        if not frames:

            return pd.DataFrame()

        combined = pd.concat(
            frames
        )

        return self._normalize(
            combined
        )