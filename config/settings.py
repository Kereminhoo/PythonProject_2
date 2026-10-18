import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# SETTINGS V2.2 (ZERO-LOSS SWING TRADING REVISION)
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
    # MARKET (SWING TRADING ADJUSTMENTS)
    # ========================================================

    # 1 Day = 1440 Minutes. Swing Trading requires daily data.
    timeframe_minutes: int = 1440

    # Focused Tech & Stable Growth Universe for Momentum Swing Trading
    universe: tuple = (
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "META",
        "GOOGL",
        "AMD",
        "QCOM",
        "PLTR", 
        "CRWD", 
        "UBER", 
        "HOOD",
        "SPY", # MARKET REGIME İÇİN ŞART!
    )

    universe_batch_size: int = 25

    # ========================================================
    # DAILY PROFIT MANAGEMENT
    # ========================================================
    
    # In Swing Trading, daily TP is irrelevant. We ride the trend.
    daily_tp1_pct: float = 0.005
    daily_tp2_pct: float = 0.010
    daily_tp1_enabled: bool = False
    daily_tp2_enabled: bool = False

    # ========================================================
    # RISK MANAGEMENT (ZERO-LOSS REVISION)
    # ========================================================

    # İşlem başına riski tekrar altın orana (%1.5) çekiyoruz
    max_risk_per_trade_pct: float = 0.015

    # Aynı anda 3 hissede en fazla %4.5 açık risk
    max_total_open_risk_pct: float = 0.045

    # Günlük maksimum kayıp limiti %3
    max_daily_loss_pct: float = 0.03

    # Sermayeyi 3 hisseye yoğunlaştırıyoruz (%33'lük dev pozisyonlar)
    max_position_pct: float = 0.33
    max_position_size_pct: float = 0.33

    # Odaklanılmış 3 kaliteli işlem
    max_open_positions: int = 3

    # ========================================================
    # INITIAL STOP
    # ========================================================

    # Stop mesafesini biraz daraltıyoruz (Daha büyük lot açabilmek için)
    atr_stop_multiplier: float = 1.5 

    # ========================================================
    # FIXED TARGET
    # ========================================================

    risk_reward_ratio: float = 1.0
    use_fixed_target: bool = False

    # ========================================================
    # V2 TRAILING STOP (ZERO-LOSS / FAST LOCK)
    # ========================================================

    # Hisse sadece %75 (0.75R) kâra geçtiği anda stop'u giriş fiyatına (başa baş) çeker!
    break_even_at_r: float = 0.75 

    # +1.2R kâr gördüğümüzde kârın en az 0.5R'sini cebe kilitliyoruz
    lock_profit_at_r: float = 1.2
    lock_profit_r: float = 0.5

    # ATR Trailing (Trend takibi) çok daha erken devreye girer
    trailing_start_at_r: float = 1.5
    trailing_atr_multiplier: float = 1.5

    trailing_only_moves_up: bool = True

    # ========================================================
    # STRATEGY (DAILY CHART PARAMETERS)
    # ========================================================

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # 20-day SMA for volume is standard for daily charts
    volume_sma_period: int = 20

    minimum_buy_score: int = 60

    # ========================================================
    # MARKET REGIME
    # ========================================================

    block_bear_market: bool = True

    # ========================================================
    # TRADE MANAGEMENT
    # ========================================================

    # Wait 1 day before re-entering the same stock after an exit
    cooldown_bars: int = 1

    # ========================================================
    # MICRO ACCOUNT
    # ========================================================

    # Küçük hesap limitlerini tamamen kapatıyoruz
    micro_account_mode: bool = False
    micro_max_open_positions: int = 1

    # ========================================================
    # EXECUTION SAFETY
    # ========================================================

    allow_fractional_shares: bool = True


# ============================================================
# LOAD SETTINGS
# ============================================================

def load_settings() -> Settings:

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key:
        raise ValueError("ALPACA_API_KEY .env dosyasında bulunamadı.")

    if not secret_key:
        raise ValueError("ALPACA_SECRET_KEY .env dosyasında bulunamadı.")

    return Settings(
        alpaca_api_key=api_key,
        alpaca_secret_key=secret_key,
    )