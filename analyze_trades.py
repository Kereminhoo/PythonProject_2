from __future__ import annotations
import math
import glob
import pandas as pd

REPORT_VERSION = "V3.0-Quant-Autopsy"

def print_separator():
    print("=" * 76)

def safe_mean(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    return float(series.mean()) if not series.empty else 0.0

def safe_sum(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    return float(series.sum()) if not series.empty else 0.0

def calculate_profit_factor(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    profits = pd.to_numeric(df.loc[df["pnl"] > 0, "pnl"], errors="coerce").dropna()
    losses = pd.to_numeric(df.loc[df["pnl"] < 0, "pnl"], errors="coerce").dropna()
    gross_profit = float(profits.sum())
    gross_loss = abs(float(losses.sum()))
    if gross_loss == 0: return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss

def calculate_group_stats(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    if group_column not in df.columns: return pd.DataFrame()
    working = df[df[group_column].notna()].copy()
    if working.empty: return pd.DataFrame()
    return (
        working.groupby(group_column, observed=False, dropna=False)
        .agg(
            Trades=("pnl", "count"),
            Win_Rate=("is_win", lambda x: x.mean() * 100.0),
            Total_PnL=("pnl", "sum"),
            Avg_PnL=("pnl", "mean"),
            Avg_R=("r_multiple", "mean"),
            Avg_Hold_Days=("holding_days", "mean"),
        )
        .sort_values("Total_PnL", ascending=False)
        .round(3)
    )

def analyze_backtest_data():
    csv_files = sorted(glob.glob("trade_analytics_20*.csv"))
    if not csv_files:
        print("Hata: 'trade_analytics_202X.csv' bulunamadı. Önce main.py çalıştırın.")
        return

    df_list = [pd.read_csv(f) for f in csv_files if not pd.read_csv(f).empty]
    if not df_list:
        return

    df = pd.concat(df_list, ignore_index=True)

    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df["exit_time"] = pd.to_datetime(df["exit_time"], errors="coerce")
    df["year"] = df["entry_time"].dt.year
    df["entry_day"] = df["entry_time"].dt.day_name()

    num_cols = [
        "entry_price", "exit_price", "quantity", "pnl", "pnl_pct", "rsi",
        "volume_ratio", "atr", "stop_distance", "position_value", "risk_amount",
        "holding_minutes", "technical_score", "fundamental_score", "alpha_score",
        "exposure_pct", "highest_price", "stop_r", "final_r"
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["is_win"] = df["pnl"] > 0
    df["is_loss"] = df["pnl"] < 0
    df["r_multiple"] = df["pnl"] / df["risk_amount"].replace(0, pd.NA)
    df["holding_days"] = df["holding_minutes"] / 1440.0

    # Maksimum Ulaşılan R (MFE - Maximum Favorable Excursion)
    if "highest_price" in df.columns and "stop_distance" in df.columns:
        df["max_reached_r"] = (df["highest_price"] - df["entry_price"]) / df["stop_distance"].replace(0, pd.NA)
        df["gave_back_r"] = df["max_reached_r"] - df["r_multiple"]

    print_separator()
    print(f"QUANT AUTOPSY REPORT ({REPORT_VERSION}) - {len(df)} TRADES")
    print_separator()

    # 1. REJİM PERFORMANSI (2022 SIZINTISI NEREDE?)
    if "market_regime" in df.columns:
        print("[1. MARKET REGIME AUTOPSY (REJİM BAZLI PERFORMANS)]")
        print(calculate_group_stats(df, "market_regime").to_string())
        print()

    # 2. STOP MANAGEMENT OTOPSİSİ (ERKEN Mİ İNİYORUZ?)
    if "last_stop_management" in df.columns:
        df["stop_stage"] = df["last_stop_management"].fillna("INITIAL_STOP_LOSS (-1R)")
        print("[2. EXIT STAGE AUTOPSY (HANGİ STOP KADEMESİNDE ÇIKIYORUZ?)]")
        stage_cols = ["pnl", "is_win", "r_multiple", "holding_days"]
        agg_dict = dict(
            Trades=("pnl", "count"),
            Win_Rate=("is_win", lambda x: x.mean() * 100.0),
            Total_PnL=("pnl", "sum"),
            Avg_Exit_R=("r_multiple", "mean"),
            Avg_Hold_Days=("holding_days", "mean"),
        )
        if "max_reached_r" in df.columns:
            agg_dict["Avg_Peak_R"] = ("max_reached_r", "mean")
            agg_dict["Avg_GaveBack_R"] = ("gave_back_r", "mean")

        stage_stats = df.groupby("stop_stage", dropna=False).agg(**agg_dict).round(3)
        print(stage_stats.to_string())
        print()

    # 3. KAYBEDEN İŞLEMLERİN SÜRE ANALİZİ (TIME-STOP FIRSATI)
    losses_df = df[df["is_loss"]].copy()
    if not losses_df.empty:
        print("[3. LOSING TRADES AUTOPSY (KAYIPLAR NEDEN OLUYOR?)]")
        slow_bleed = losses_df[losses_df["holding_days"] >= 5.0]
        fast_stop = losses_df[losses_df["holding_days"] < 5.0]
        print(f" - Hızlı Stop (<5 Gün)      : {len(fast_stop)} işlem | Toplam Zarar: ${safe_sum(fast_stop['pnl']):.2f} | Ort Peak R: {safe_mean(fast_stop.get('max_reached_r', pd.Series())):.2f}R")
        print(f" - Yavaş Erime (>=5 Gün)    : {len(slow_bleed)} işlem | Toplam Zarar: ${safe_sum(slow_bleed['pnl']):.2f} | Ort Peak R: {safe_mean(slow_bleed.get('max_reached_r', pd.Series())):.2f}R")
        print()

    # 4. MASADA BIRAKILAN KÂRLAR (CHOKED WINNERS)
    if "max_reached_r" in df.columns:
        choked = df[(df["max_reached_r"] >= 1.5) & (df["r_multiple"] <= 0.35)].copy()
        print(f"[4. CHOKED WINNERS (+1.5R GÖRÜP <0.35R İLE KAPANANLAR): {len(choked)} İŞLEM]")
        if not choked.empty:
            cols = ["symbol", "year", "entry_price", "highest_price", "exit_price", "max_reached_r", "r_multiple", "pnl"]
            print(choked[cols].sort_values("max_reached_r", ascending=False).head(10).round(2).to_string(index=False))
        print()

    # 5. EN BÜYÜK 10 ZARAR
    print("[5. TOP 10 WORST LOSING TRADES]")
    worst_cols = [c for c in ["symbol", "year", "market_regime", "technical_score", "alpha_score", "rsi", "holding_days", "max_reached_r", "r_multiple", "pnl"] if c in df.columns]
    print(df.sort_values("pnl").head(10)[worst_cols].round(2).to_string(index=False))
    print()

if __name__ == "__main__":
    analyze_backtest_data()