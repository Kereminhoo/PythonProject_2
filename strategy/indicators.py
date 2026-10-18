from __future__ import annotations

import pandas as pd

from ta.trend import (
    MACD,
    EMAIndicator,
    SMAIndicator,
    ADXIndicator,
    IchimokuIndicator,
)

from ta.momentum import (
    RSIIndicator,
)

from ta.volatility import (
    AverageTrueRange,
    BollingerBands,
)

from ta.volume import (
    OnBalanceVolumeIndicator,
    ChaikinMoneyFlowIndicator,
)


class IndicatorEngine:

    # ============================================================
    # STANDARD PARAMETERS (SWING TRADING FOCUS)
    # ============================================================

    EMA_FAST_PATTERN = 5
    EMA_SLOW_PATTERN = 7

    EMA_FAST_LEGACY = 9
    EMA_SLOW_LEGACY = 21
    
    # SWING TRADING LONG TERM TREND (Golden Cross / Death Cross)
    EMA_TREND_MID = 50
    SMA_TREND_LONG = 200

    SMA_TREND_WINDOW = 20

    RSI_WINDOW = 14
    ATR_WINDOW = 14

    BB_WINDOW = 20
    BB_STD = 2

    ICHIMOKU_CONVERSION = 9
    ICHIMOKU_BASE = 26
    ICHIMOKU_SPAN_B = 52

    ADX_WINDOW = 14

    OBV_SMOOTH_WINDOW = 20
    CMF_WINDOW = 20

    # ============================================================
    # INIT
    # ============================================================

    def __init__(
        self,
        settings,
    ):

        self.settings = settings

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _zlema(
        series: pd.Series,
        window: int,
    ) -> pd.Series:
        """
        Zero-Lag EMA.

        DEMA tabanlı zero-lag EMA:

            EMA1 = EMA(price)
            EMA2 = EMA(EMA1)

            ZLEMA = 2 * EMA1 - EMA2

        Sadece mevcut ve geçmiş değerleri kullanır.
        """

        window = int(window)

        if window <= 0:
            raise ValueError(
                "ZLEMA window 0'dan büyük olmalıdır."
            )

        ema_1 = (
            series
            .ewm(
                span=window,
                adjust=False,
                min_periods=window,
            )
            .mean()
        )

        ema_2 = (
            ema_1
            .ewm(
                span=window,
                adjust=False,
                min_periods=window,
            )
            .mean()
        )

        return (
            2.0 * ema_1
            - ema_2
        )

    # ============================================================
    # CALCULATE
    # ============================================================

    def calculate(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Teknik göstergeleri hesaplar.
        SWING TRADING V2 (Daily Timeframe Focus)
        """

        if df is None:
            raise ValueError(
                "IndicatorEngine: df None olamaz."
            )

        data = df.copy()

        required_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in data.columns
        ]

        if missing_columns:

            raise ValueError(
                "Eksik market kolonları: "
                + ", ".join(
                    missing_columns
                )
            )

        # ========================================================
        # MACD - LEGACY
        # ========================================================

        macd_fast = int(
            getattr(
                self.settings,
                "macd_fast",
                12,
            )
        )

        macd_slow = int(
            getattr(
                self.settings,
                "macd_slow",
                26,
            )
        )

        macd_signal = int(
            getattr(
                self.settings,
                "macd_signal",
                9,
            )
        )

        macd = MACD(
            close=data["close"],
            window_fast=macd_fast,
            window_slow=macd_slow,
            window_sign=macd_signal,
        )

        data["macd"] = macd.macd()
        data["macd_signal"] = macd.macd_signal()
        data["macd_histogram"] = macd.macd_diff()

        # ========================================================
        # EMA 5 / 7
        # ========================================================

        ema_5 = EMAIndicator(close=data["close"], window=self.EMA_FAST_PATTERN)
        ema_7 = EMAIndicator(close=data["close"], window=self.EMA_SLOW_PATTERN)

        data["ema_5"] = ema_5.ema_indicator()
        data["ema_7"] = ema_7.ema_indicator()
        data["ema_5_slope"] = data["ema_5"].diff()
        data["ema_7_slope"] = data["ema_7"].diff()
        data["ema_5_7_gap_pct"] = (data["ema_5"] / data["ema_7"]) - 1.0

        # ========================================================
        # EMA 9 / 21
        # ========================================================

        ema_fast = EMAIndicator(close=data["close"], window=self.EMA_FAST_LEGACY)
        ema_slow = EMAIndicator(close=data["close"], window=self.EMA_SLOW_LEGACY)

        data["ema_9"] = ema_fast.ema_indicator()
        data["ema_21"] = ema_slow.ema_indicator()
        data["ema_gap_pct"] = (data["ema_9"] / data["ema_21"]) - 1.0
        data["ema_9_slope"] = data["ema_9"].diff()
        data["ema_21_slope"] = data["ema_21"].diff()
        
        # ========================================================
        # LONG TERM TREND (50 EMA & 200 SMA)
        # ========================================================
        
        ema_50 = EMAIndicator(close=data["close"], window=self.EMA_TREND_MID)
        sma_200 = SMAIndicator(close=data["close"], window=self.SMA_TREND_LONG)
        
        data["ema_50"] = ema_50.ema_indicator()
        data["sma_200"] = sma_200.sma_indicator()
        data["price_vs_ema50"] = (data["close"] / data["ema_50"]) - 1.0
        data["price_vs_sma200"] = (data["close"] / data["sma_200"]) - 1.0

        # ========================================================
        # SMA 20
        # ========================================================

        sma_20 = SMAIndicator(close=data["close"], window=self.SMA_TREND_WINDOW)
        data["sma_20"] = sma_20.sma_indicator()
        data["sma_20_slope"] = data["sma_20"].diff()
        data["price_vs_sma20"] = (data["close"] / data["sma_20"]) - 1.0

        # ========================================================
        # RSI
        # ========================================================

        rsi = RSIIndicator(close=data["close"], window=self.RSI_WINDOW)
        data["rsi"] = rsi.rsi()
        data["rsi_slope"] = data["rsi"].diff()

        # ========================================================
        # ATR
        # ========================================================

        atr = AverageTrueRange(
            high=data["high"],
            low=data["low"],
            close=data["close"],
            window=self.ATR_WINDOW,
        )

        data["atr"] = atr.average_true_range()
        data["atr_pct"] = data["atr"] / data["close"]
        data["atr_slope"] = data["atr"].diff()
        data["atr_pct_change"] = data["atr_pct"].pct_change()

        # ========================================================
        # BOLLINGER BANDS 20 / 2
        # ========================================================

        bollinger = BollingerBands(
            close=data["close"],
            window=self.BB_WINDOW,
            window_dev=self.BB_STD,
        )

        data["bb_middle"] = bollinger.bollinger_mavg()
        data["bb_upper"] = bollinger.bollinger_hband()
        data["bb_lower"] = bollinger.bollinger_lband()
        data["bb_pct_b"] = bollinger.bollinger_pband()
        data["bb_width"] = bollinger.bollinger_wband()
        data["bb_middle_slope"] = data["bb_middle"].diff()
        data["bb_width_change"] = data["bb_width"].diff()
        data["price_vs_bb_middle"] = (data["close"] / data["bb_middle"]) - 1.0

        # ========================================================
        # ICHIMOKU
        # ========================================================

        ichimoku = IchimokuIndicator(
            high=data["high"],
            low=data["low"],
            window1=self.ICHIMOKU_CONVERSION,
            window2=self.ICHIMOKU_BASE,
            window3=self.ICHIMOKU_SPAN_B,
            visual=False,
        )

        data["ichimoku_tenkan"] = ichimoku.ichimoku_conversion_line()
        data["ichimoku_kijun"] = ichimoku.ichimoku_base_line()
        data["ichimoku_span_a"] = ichimoku.ichimoku_a()
        data["ichimoku_span_b"] = ichimoku.ichimoku_b()

        data["ichimoku_cloud_top"] = pd.concat(
            [data["ichimoku_span_a"], data["ichimoku_span_b"]], axis=1
        ).max(axis=1)

        data["ichimoku_cloud_bottom"] = pd.concat(
            [data["ichimoku_span_a"], data["ichimoku_span_b"]], axis=1
        ).min(axis=1)

        data["ichimoku_cloud_width"] = data["ichimoku_cloud_top"] - data["ichimoku_cloud_bottom"]
        data["ichimoku_cloud_bullish"] = data["ichimoku_span_a"] > data["ichimoku_span_b"]
        data["ichimoku_price_above_cloud"] = data["close"] > data["ichimoku_cloud_top"]
        data["ichimoku_tenkan_above_kijun"] = data["ichimoku_tenkan"] > data["ichimoku_kijun"]

        # ========================================================
        # CHIKOU
        # ========================================================

        chikou_lag = self.ICHIMOKU_BASE
        data["chikou_close"] = data["close"].shift(chikou_lag)
        data["chikou_bullish"] = data["close"] > data["close"].shift(chikou_lag)

        # ========================================================
        # ADX / DMI
        # ========================================================

        adx = ADXIndicator(
            high=data["high"],
            low=data["low"],
            close=data["close"],
            window=self.ADX_WINDOW,
        )

        data["adx"] = adx.adx()
        data["di_plus"] = adx.adx_pos()
        data["di_minus"] = adx.adx_neg()
        data["adx_slope"] = data["adx"].diff()
        data["dmi_bullish"] = data["di_plus"] > data["di_minus"]

        # ========================================================
        # VOLUME SMA & RELATIVE VOLUME (REVISED FOR SWING)
        # ========================================================

        volume_period = int(getattr(self.settings, "volume_sma_period", 20))
        
        data["volume_sma"] = data["volume"].rolling(window=volume_period).mean()
        
        # Simple Daily Volume Breakout Check
        data["volume_ratio"] = data["volume"] / data["volume_sma"]
        data["volume_breakout"] = data["volume_ratio"] > 1.5

        # ========================================================
        # OBV
        # ========================================================

        obv = OnBalanceVolumeIndicator(close=data["close"], volume=data["volume"])
        data["obv"] = obv.on_balance_volume()
        data["obv_sma"] = data["obv"].rolling(window=self.OBV_SMOOTH_WINDOW).mean()
        data["obv_slope"] = data["obv"].diff()
        data["obv_bullish"] = data["obv"] > data["obv_sma"]

        # ========================================================
        # CHAIKIN MONEY FLOW
        # ========================================================

        cmf = ChaikinMoneyFlowIndicator(
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"],
            window=self.CMF_WINDOW,
        )

        data["cmf"] = cmf.chaikin_money_flow()
        data["cmf_slope"] = data["cmf"].diff()
        data["cmf_bullish"] = data["cmf"] > 0

        # ========================================================
        # MOMENTUM (RETURNS)
        # ========================================================

        data["return_1"] = data["close"].pct_change(1)
        data["return_3"] = data["close"].pct_change(3)
        data["return_6"] = data["close"].pct_change(6)

        # ========================================================
        # ZERO-LAG MACD
        # ========================================================

        zl_fast = self._zlema(data["close"], macd_fast)
        zl_slow = self._zlema(data["close"], macd_slow)

        data["zl_macd"] = zl_fast - zl_slow
        data["zl_macd_signal"] = self._zlema(data["zl_macd"], macd_signal)
        data["zl_macd_histogram"] = data["zl_macd"] - data["zl_macd_signal"]
        data["zl_macd_slope"] = data["zl_macd"].diff()
        data["zl_macd_signal_slope"] = data["zl_macd_signal"].diff()
        data["zl_macd_bullish"] = data["zl_macd"] > data["zl_macd_signal"]
        data["zl_macd_above_zero"] = data["zl_macd"] > 0
        data["macd_strength"] = data["macd_histogram"] / data["atr"]
        data["zl_macd_strength"] = data["zl_macd_histogram"] / data["atr"]

        # ========================================================
        # CANDLE STRUCTURE
        # ========================================================

        data["candle_range"] = data["high"] - data["low"]
        data["candle_body"] = (data["close"] - data["open"]).abs()
        data["candle_body_pct"] = data["candle_body"] / data["candle_range"]
        data["candle_upper_wick"] = data["high"] - data[["open", "close"]].max(axis=1)
        data["candle_lower_wick"] = data[["open", "close"]].min(axis=1) - data["low"]
        data["candle_bullish"] = data["close"] > data["open"]
        data["candle_close_position"] = (data["close"] - data["low"]) / data["candle_range"]

        # ========================================================
        # SHORT-TERM PRICE STRUCTURE
        # ========================================================

        data["previous_high"] = data["high"].shift(1)
        data["previous_low"] = data["low"].shift(1)
        data["highest_10"] = data["high"].rolling(window=10).max().shift(1)
        data["lowest_10"] = data["low"].rolling(window=10).min().shift(1)
        data["breakout_above_10"] = data["close"] > data["highest_10"]
        data["breakdown_below_10"] = data["close"] < data["lowest_10"]

        # ========================================================
        # CLEANUP
        # ========================================================

        data = data.replace([float("inf"), float("-inf")], pd.NA)

        return data