import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# SETTINGS V3.0 (HIGH-VELOCITY COMPOUNDING ENGINE)
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
    # MARKET (HIGH-BETA SWING UNIVERSE)
    # ========================================================

    timeframe_minutes: int = 1440

    # Hantal hisseler (AAPL, MSFT, AMZN, UBER, CRWD) çıkarıldı.
    # Sadece yüksek momentum ve yüksek R-Multiple üreten liderler + SPY (Rejim için)
    universe: tuple = (
        "NVDA",
        "AMD",
        "PLTR",
        "QCOM",
        "META",
        "GOOGL",
        "HOOD",
        "AVGO",  # Yarı iletken lideri - Yüksek Trend Kalitesi
        "MU",    # Güçlü Swing dalgaları
        "ANET",  # AI Altyapı lideri - Temiz kırılımlar
        "PANW",  # Siber güvenlik lideri (CRWD yerine)
        "COIN",  # Kripto/Fintech yüksek Beta patlamaları
        "SPY",   # SADECE MARKET REGIME İÇİN (Alım-Satıma kapatılacak)
    )

    # İşlem yapılması yasak olan (Sadece referans/endeks) semboller
    non_tradable_symbols: tuple = ("SPY", "TSLA")

    universe_batch_size: int = 25

    # ========================================================
    # DAILY PROFIT MANAGEMENT (SWING'DE KAPALI)
    # ========================================================
    
    daily_tp1_pct: float = 0.005
    daily_tp2_pct: float = 0.010
    daily_tp1_enabled: bool = False
    daily_tp2_enabled: bool = False

    # ========================================================
    # AGGRESSIVE RISK & POSITION SIZING (V3.0)
    # ========================================================

    # Baz işlem riski %1.5'ten %2.25'e çıkarıldı (Drawdown'ımız sadece %6 olduğu için güvenli alanımız geniş)
    max_risk_per_trade_pct: float = 0.0225

    # Dinamik Alpha Riski (Elit sinyallerde mermiyi büyütür)
    use_dynamic_risk: bool = True
    high_alpha_threshold: float = 85.0
    high_alpha_risk_pct: float = 0.0325  # 85+ Alpha skorunda %3.25 risk

    # Toplam açık risk limiti (%9.0 - 3 güçlü pozisyona tam izin verir)
    max_total_open_risk_pct: float = 0.090

    # Günlük maksimum kayıp limiti %4.5
    max_daily_loss_pct: float = 0.045

    # KRİTİK FREN KALDIRILDI: %33 sınırı %55'e çıkarıldı!
    # Artık pozisyon büyüklüğü tırpanlanmayacak, gerçek R riski alınabilecek.
    max_position_pct: float = 0.55
    max_position_size_pct: float = 0.55

    # Aynı anda maksimum 3 odaklanmış pozisyon
    max_open_positions: int = 3

    # ========================================================
    # INITIAL STOP & FIXED TARGET
    # ========================================================

    atr_stop_multiplier: float = 1.5 

    risk_reward_ratio: float = 1.0
    use_fixed_target: bool = False

    # ========================================================
    # V3.0 SMART TRAILING & PARABOLIC LOCK
    # ========================================================

    # 0.70R'ye ulaşıldığında stop'u 0.0R'ye değil, +0.20R kâra çeker! (37 işlemi kârlı kapatır)
    break_even_at_r: float = 0.70 
    break_even_offset_r: float = 0.20

    # +1.2R kârda 0.65R'yi cebe kilitler
    lock_profit_at_r: float = 1.20
    lock_profit_r: float = 0.65

    # Trend takibi (+1.5R'de başlar)
    trailing_start_at_r: float = 1.50
    trailing_atr_multiplier: float = 1.40

    # Parabolik Sıkılaştırma (RSI > 75 olduğunda kârı zirvede kilitlemek için daraltılmış ATR)
    parabolic_rsi_threshold: float = 75.0
    parabolic_atr_multiplier: float = 0.85

    trailing_only_moves_up: bool = True

    # ========================================================
    # STRATEGY (SELECTIVE SNIPER)
    # ========================================================

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    volume_sma_period: int = 20

    # Kalitesiz işlemleri elemek için minimum skor 60'tan 68'e çıkarıldı
    minimum_buy_score: int = 68

    # ========================================================
    # MARKET REGIME & TRADE MANAGEMENT
    # ========================================================

    block_bear_market: bool = True
    cooldown_bars: int = 1

    micro_account_mode: bool = False
    micro_max_open_positions: int = 1

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