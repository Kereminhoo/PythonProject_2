import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


# ============================================================
# SETTINGS V2
# ============================================================

@dataclass(frozen=True)
class Settings:

    # ========================================================
    # ALPACA
    # ========================================================

    alpaca_api_key: str
    alpaca_secret_key: str

    paper_trading: bool = True

    # ========================================================
    # MARKET
    # ========================================================

    timeframe_minutes: int = 5

    universe: tuple = (
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "META",
        "GOOGL",
        "GOOG",
        "AVGO",
        "TSLA",
        "AMD",
        "NFLX",
        "ORCL",
        "ADBE",
        "CRM",
        "QCOM",
        "JPM",
        "V",
        "MA",
        "XOM",
        "CVX",
        "WMT",
        "COST",
        "KO",
        "PEP",
        "SPY",
    )

    universe_batch_size: int = 25

    # ========================================================
    # DAILY PROFIT MANAGEMENT
    # ========================================================

    # Bunlar artık "hard take-profit" değildir.
    # Günlük performans analizinde kullanılabilir.
    daily_tp1_pct: float = 0.005
    daily_tp2_pct: float = 0.010

    # V2'de günlük +0.5% geldi diye yeni trade açmayı
    # otomatik olarak durdurmuyoruz.
    daily_tp1_enabled: bool = False

    # V2'de günlük +1% geldi diye bütün pozisyonları
    # otomatik kapatmıyoruz.
    daily_tp2_enabled: bool = False

    # ========================================================
    # RISK MANAGEMENT
    # ========================================================

    # Tek trade maksimum başlangıç riski.
    # 0.01 = %1
    max_risk_per_trade_pct: float = 0.01

    # Açık pozisyonların toplam başlangıç riski.
    # 0.02 = %2
    max_total_open_risk_pct: float = 0.02

    # Günlük maksimum zarar.
    # 0.02 = %2
    max_daily_loss_pct: float = 0.02

    # Tek pozisyon maksimum exposure.
    # 0.25 = %25
    max_position_pct: float = 0.25

    # PositionSizer compatibility.
    max_position_size_pct: float = 0.25

    # V2:
    # Çok fazla eşzamanlı pozisyon yerine seçilmiş
    # yüksek kaliteli trade'lere odaklanıyoruz.
    max_open_positions: int = 2

    # ========================================================
    # INITIAL STOP
    # ========================================================

    # İlk stop ATR tabanlı.
    #
    # Örnek:
    # ATR = 1.00
    # multiplier = 1.5
    # stop distance = 1.50
    #
    # Eski kod ile compatibility amacıyla
    # atr_stop_multiplier ismi korunuyor.
    atr_stop_multiplier: float = 1.5

    # ========================================================
    # FIXED TARGET
    # ========================================================

    # V2'de sabit TP ana çıkış yöntemi değil.
    #
    # PositionSizer eski API'yi kullanmaya devam edebileceği
    # için risk_reward_ratio tutuluyor.
    risk_reward_ratio: float = 1.0

    use_fixed_target: bool = False

    # ========================================================
    # V2 TRAILING STOP
    # ========================================================

    # --------------------------------------------------------
    # BREAK-EVEN
    # --------------------------------------------------------

    # Trade +1R olduğunda stop giriş seviyesine taşınır.
    break_even_at_r: float = 1.0

    # --------------------------------------------------------
    # PROFIT LOCK
    # --------------------------------------------------------

    # Trade +1.5R olduğunda kâr korunmaya başlanır.
    lock_profit_at_r: float = 1.5

    # +1.5R seviyesinde en az +0.5R korunur.
    lock_profit_r: float = 0.5

    # --------------------------------------------------------
    # ATR TRAILING
    # --------------------------------------------------------

    # ATR trailing +2R sonrasında devreye girer.
    trailing_start_at_r: float = 2.0

    # Stop fiyatının current price arkasında
    # tutulacağı ATR mesafesi.
    trailing_atr_multiplier: float = 1.5

    # Stop hiçbir zaman geriye çekilmez.
    trailing_only_moves_up: bool = True

    # ========================================================
    # STRATEGY
    # ========================================================

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    volume_sma_period: int = 10

    # V2'de sadece yüksek kaliteli teknik setup'ları
    # almaya başlayacağız.
    minimum_buy_score: int = 75

    # ========================================================
    # MARKET REGIME
    # ========================================================

    # BEAR rejiminde long işlemler bloklanmaya devam eder.
    block_bear_market: bool = True

    # ========================================================
    # TRADE MANAGEMENT
    # ========================================================

    cooldown_bars: int = 6

    # ========================================================
    # MICRO ACCOUNT
    # ========================================================

    # €50 gibi küçük hesaplarda özel kuralları
    # aktif edebilmek için.
    micro_account_mode: bool = True

    # Çok küçük hesaplarda birden fazla pozisyonun
    # sermayeyi anlamsız şekilde bölmesini önlemek için.
    micro_max_open_positions: int = 1

    # ========================================================
    # EXECUTION SAFETY
    # ========================================================

    # Alpaca fractional quantity kullanılacağı için
    # quantity float olarak tutulabilir.
    allow_fractional_shares: bool = True


# ============================================================
# LOAD SETTINGS
# ============================================================

def load_settings() -> Settings:

    api_key = os.getenv(
        "ALPACA_API_KEY"
    )

    secret_key = os.getenv(
        "ALPACA_SECRET_KEY"
    )

    if not api_key:
        raise ValueError(
            "ALPACA_API_KEY .env dosyasında bulunamadı."
        )

    if not secret_key:
        raise ValueError(
            "ALPACA_SECRET_KEY .env dosyasında bulunamadı."
        )

    return Settings(
        alpaca_api_key=api_key,
        alpaca_secret_key=secret_key,
    )