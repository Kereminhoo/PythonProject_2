import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# SETTINGS V3.3 (1000$+ TARGET - NO EARLY CHOKE EDITION)
# ============================================================

@dataclass(frozen=True)
class Settings:

    alpaca_api_key: str
    alpaca_secret_key: str
    paper_trading: bool = True

    timeframe_minutes: int = 1440

    # En yüksek R-Multiple üreten çekirdek liderler
    universe: tuple = (
        "NVDA",
        "AMD",
        "PLTR",
        "QCOM",
        "GOOGL",
        "HOOD",
        "AVGO",
        "MU",
        "ANET",
        "COIN",
        "SPY",   # Sadece Market Regime için
    )

    non_tradable_symbols: tuple = ("SPY", "TSLA")
    universe_batch_size: int = 25

    daily_tp1_pct: float = 0.005
    daily_tp2_pct: float = 0.010
    daily_tp1_enabled: bool = False
    daily_tp2_enabled: bool = False

    # ========================================================
    # FULL-THROTTLE RISK & EXPOSURE (V3.3)
    # ========================================================

    # İşlem başı risk %4.25! (Drawdown çok düşük olduğu için tam kapasite)
    max_risk_per_trade_pct: float = 0.0425
    max_total_open_risk_pct: float = 0.160
    max_daily_loss_pct: float = 0.075

    # Pozisyonların %50'de kırpılmasını önlemek için %80 Exposure tavanı (2.5x BP ile)
    max_position_pct: float = 0.80
    max_position_size_pct: float = 0.80

    max_open_positions: int = 3

    atr_stop_multiplier: float = 1.5 
    risk_reward_ratio: float = 1.0
    use_fixed_target: bool = False

    # ========================================================
    # V3.3 PURE WINNING TRAILING (NO EARLY_SHIELD LOSSES!)
    # ========================================================

    # EARLY_SHIELD kaldırıldı!
    # Hisse +0.75R'ye ulaştığı an stop doğrudan +0.20R POZİTİF KÂRA çekilir (%100 Win Rate kademesi!)
    break_even_at_r: float = 0.75 
    break_even_offset_r: float = 0.20

    # +1.30R'de +0.70R kârı cebe kilitler
    lock_profit_at_r: float = 1.30
    lock_profit_r: float = 0.70

    # +1.70R'de ATR Trailing başlar
    trailing_start_at_r: float = 1.70
    trailing_atr_multiplier: float = 1.45

    # Parabolik Zirve Kilidi (En çok para kazandıran kademe: $415 PnL!)
    parabolic_rsi_threshold: float = 77.0
    parabolic_atr_multiplier: float = 0.85

    # Zaman Stobu: 7 gün sonunda hiç +0.40R görememiş ve eksedeki ölü işlemleri kapatır
    time_stop_bars: int = 7

    trailing_only_moves_up: bool = True

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    volume_sma_period: int = 20

    # Zayıf sinyalleri (66-69 puan) kesmek için 70 puan barajı!
    minimum_buy_score: int = 70

    block_bear_market: bool = True
    cooldown_bars: int = 1

    micro_account_mode: bool = False
    micro_max_open_positions: int = 1
    allow_fractional_shares: bool = True


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