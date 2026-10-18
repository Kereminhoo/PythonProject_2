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
    # TIMEFRAME (SWING TRADING REVISION)
    # ==================================================

    def _timeframe(self):
        """
        Alpaca API limits minutes to 1-59.
        If timeframe_minutes is 1440 or higher, switch to Daily timeframe.
        """
        minutes = self.settings.timeframe_minutes

        if minutes >= 1440:
            days = minutes // 1440
            return TimeFrame(
                days,
                TimeFrameUnit.Day,
            )
        elif minutes >= 60:
            hours = minutes // 60
            return TimeFrame(
                hours,
                TimeFrameUnit.Hour,
            )
        else:
            return TimeFrame(
                minutes,
                TimeFrameUnit.Minute,
            )

    # ==================================================
    # RECENT DATA
    # ==================================================

    def get_recent_bars(self):

        end_time = datetime.now(
            timezone.utc
        )
        
        # Extended fetch period for daily charts (Swing Trading needs more history)
        start_time = (
            end_time
            - timedelta(days=60) # Increased from 5 days to 60 days
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