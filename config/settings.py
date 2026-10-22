import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# SETTINGS V3.8 (ALL-WEATHER FORTRESS & 1200$+ TARGET)
# ============================================================

@dataclass(frozen=True)
class Settings:

    alpaca_api_key: str
    alpaca_secret_key: str
    paper_trading: bool = True

    timeframe_minutes: int = 1440

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
    # FULL-THROTTLE COMPOUNDING RISK (V3.8)
    # ========================================================

    max_risk_per_trade_pct: float = 0.050
    max_total_open_risk_pct: float = 0.180
    max_daily_loss_pct: float = 0.085

    max_position_pct: float = 0.85
    max_position_size_pct: float = 0.85

    max_open_positions: int = 3

    atr_stop_multiplier: float = 1.5 
    risk_reward_ratio: float = 1.0
    use_fixed_target: bool = False

    # ========================================================
    # V3.8 ADAPTIVE TRAILING STOP (SAVES 0.65R+ & RIDES 2024/2025)
    # ========================================================

    # 0.65R gören işlem (AVGO +0.70R, COIN +0.69R) asla -1R zarar yazamaz!
    # Doğrudan +0.20R pozitif kâra kilitlenir!
    break_even_at_r: float = 0.65 
    break_even_offset_r: float = 0.20

    # +1.28R'de +0.70R kârı cebe kilitler
    lock_profit_at_r: float = 1.28
    lock_profit_r: float = 0.70

    # +1.70R'de ATR Trailing başlar
    trailing_start_at_r: float = 1.70
    trailing_atr_multiplier: float = 1.45

    # Parabolik Zirve Kilidi ($755+ PnL üreten altın eşik: RSI 77.0)
    parabolic_rsi_threshold: float = 77.0
    parabolic_atr_multiplier: float = 0.85

    # Zaman Stobu: 6 gün sonunda hâlâ Break-Even olamamış ve eksedeki ölü işlemleri keser
    time_stop_bars: int = 6

    trailing_only_moves_up: bool = True

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    volume_sma_period: int = 20

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