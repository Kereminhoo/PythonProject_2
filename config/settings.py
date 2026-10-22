import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# SETTINGS V4.0 (ADAPTIVE CHAMELEON & MULTI-SECTOR EDITION)
# ============================================================

@dataclass(frozen=True)
class Settings:

    alpaca_api_key: str
    alpaca_secret_key: str
    paper_trading: bool = True

    timeframe_minutes: int = 1440

    # Teknoloji Liderleri + 2022 Krizinde Ralli Yapan Sağlık (LLY) ve Enerji (XOM) Devleri!
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
        "LLY",   # Sağlık/İlaç Lideri (2022 Ayı Piyasasında ve 2023-2024'te Dev Ralli!)
        "XOM",   # Enerji Lideri (2022 Enflasyon/Faiz Krizinde +%80 Ralli!)
        "SPY",   # Sadece Market Regime için
    )

    non_tradable_symbols: tuple = ("SPY", "TSLA")
    defensive_symbols: tuple = ("LLY", "XOM", "UNH")
    universe_batch_size: int = 25

    daily_tp1_pct: float = 0.005
    daily_tp2_pct: float = 0.010
    daily_tp1_enabled: bool = False
    daily_tp2_enabled: bool = False

    # ========================================================
    # BASE RISK & EXPOSURE (ADAPTIVE ENGINE TARAFINDAN YÖNETİLİR)
    # ========================================================

    max_risk_per_trade_pct: float = 0.0525
    max_total_open_risk_pct: float = 0.185
    max_daily_loss_pct: float = 0.085

    max_position_pct: float = 0.85
    max_position_size_pct: float = 0.85

    max_open_positions: int = 3

    atr_stop_multiplier: float = 1.5 
    risk_reward_ratio: float = 1.0
    use_fixed_target: bool = False

    # ========================================================
    # BASE TRAILING STOP (VİTESLERE GÖRE DİNAMİK ESNER)
    # ========================================================

    break_even_at_r: float = 0.75 
    break_even_offset_r: float = 0.20

    lock_profit_at_r: float = 1.30
    lock_profit_r: float = 0.70

    trailing_start_at_r: float = 1.70
    trailing_atr_multiplier: float = 1.45

    parabolic_rsi_threshold: float = 77.0
    parabolic_atr_multiplier: float = 0.85

    time_stop_bars: int = 7

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