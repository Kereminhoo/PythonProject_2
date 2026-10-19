from __future__ import annotations
import math
import os
import glob
import pandas as pd

# ============================================================
# CONFIG
# ============================================================
REPORT_VERSION = "V2.2-Quant-AI-Fresh-Scan"

# ============================================================
# HELPERS
# ============================================================
def print_separator():
    print("=" * 72)

def safe_mean(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty: return 0.0
    return float(series.mean())

def safe_sum(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty: return 0.0
    return float(series.sum())

def calculate_profit_factor(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    profits = pd.to_numeric(df.loc[df["pnl"] > 0, "pnl"], errors="coerce").dropna()
    losses = pd.to_numeric(df.loc[df["pnl"] < 0, "pnl"], errors="coerce").dropna()
    gross_profit = float(profits.sum())
    gross_loss = abs(float(losses.sum()))
    if gross_loss == 0: return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss

def calculate_win_rate(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    return float(df["is_win"].mean() * 100.0)

# ============================================================
# GROUP ANALYSIS
# ============================================================
def calculate_group_stats(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    if group_column not in df.columns: return pd.DataFrame()
    working = df[df[group_column].notna()].copy()
    if working.empty: return pd.DataFrame()
    result = (
        working.groupby(group_column, observed=False, dropna=False)
        .agg(
            Total_Trades=("pnl", "count"),
            Win_Rate=("is_win", lambda x: x.mean() * 100.0),
            Total_PnL=("pnl", "sum"),
            Average_PnL=("pnl", "mean"),
            Average_R=("r_multiple", "mean"),
        )
        .sort_values("Total_PnL", ascending=False)
        .round(4)
    )
    return result

def print_group_stats(df: pd.DataFrame, group_column: str):
    stats = calculate_group_stats(df, group_column)
    if stats.empty:
        print("Aucune donnée.")
        return
    print(stats.to_string())

REQUIRED_COLUMNS = [
    "symbol", "entry_time", "exit_time", "entry_price", "exit_price",
    "quantity", "pnl", "pnl_pct", "exit_reason", "rsi", "volume_ratio",
    "atr", "stop_distance", "target_distance", "risk_reward_ratio",
    "position_value", "risk_amount", "holding_minutes",
]

OPTIONAL_NUMERIC_COLUMNS = [
    "gross_pnl", "entry_value", "exit_value", "return_on_entry_pct",
    "entry_equity", "exposure_pct", "max_total_open_risk", "projected_open_risk",
    "signal_score", "technical_score", "fundamental_score", "alpha_score",
    "alpha_base_score", "alpha_regime_adjustment", "fundamental_data_quality"
]

CATEGORICAL_COLUMNS = ["symbol", "exit_reason", "market_regime", "alpha_mode", "reasons"]

# ============================================================
# AI QUANT INSIGHTS GENERATOR
# ============================================================
def generate_ai_insights(df: pd.DataFrame):
    print_separator()
    print("[AI QUANT ASSISTANT - ANALYSE ET RECOMMANDATIONS]")
    print_separator()
    
    insights = []
    win_rate = calculate_win_rate(df)
    pf = calculate_profit_factor(df)
    
    if win_rate < 40 and pf > 1.5:
        insights.append(f"🟢 [PROFIT ASYMÉTRIQUE]: Win rate faible ({win_rate:.1f}%) mais Profit Factor puissant ({pf:.2f}). Le trailing stop fonctionne à merveille.")
    elif win_rate > 50 and pf < 1.0:
        insights.append(f"🔴 [DANGER]: Vos pertes effacent vos gains (PF: {pf:.2f}). Resserrez vos stops.")

    if "entry_day" in df.columns:
        day_stats = calculate_group_stats(df, "entry_day")
        if not day_stats.empty:
            worst_day = day_stats.sort_values("Total_PnL").index[0]
            worst_day_pnl = day_stats.loc[worst_day, "Total_PnL"]
            if worst_day_pnl < 0:
                insights.append(f"🔴 [TIMING]: Pire journée pour entrer = {worst_day} (PnL: ${worst_day_pnl:.2f}).")
            best_day = day_stats.sort_values("Total_PnL", ascending=False).index[0]
            insights.append(f"🟢 [MEILLEUR JOUR]: Le système excelle les {best_day}.")

    avg_win_time = safe_mean(df.loc[df["is_win"], "holding_minutes"]) / 1440
    avg_loss_time = safe_mean(df.loc[df["is_loss"], "holding_minutes"]) / 1440
    if avg_loss_time > avg_win_time:
        insights.append(f"🔴 [ESPOIR FATAL]: Vous gardez les pertes plus longtemps (Moy: {avg_loss_time:.1f} jours) que les gains ({avg_win_time:.1f} jours).")
    else:
        insights.append(f"🟢 [DISCIPLINE]: Pertes coupées tôt ({avg_loss_time:.1f} j) et gains maximisés ({avg_win_time:.1f} j).")

    for insight in insights:
        print(insight)
    print()

# ============================================================
# MAIN ANALYZER
# ============================================================
def analyze_backtest_data():
    # Scanner uniquement les nouveaux fichiers csv dans le dossier principal
    csv_files = glob.glob("trade_analytics_20*.csv")
    
    if not csv_files:
        print("Aucun fichier 'trade_analytics_202X.csv' récent trouvé. Lancez d'abord main.py.")
        return

    print(f"Chargement des données fraîches... ({len(csv_files)} fichiers trouvés)")
    
    df_list = []
    for file in csv_files:
        try:
            temp_df = pd.read_csv(file)
            if not temp_df.empty:
                df_list.append(temp_df)
        except Exception as e:
            print(f"Erreur avec {file}: {e}")

    if not df_list:
        print("Les fichiers sont vides.")
        return

    df = pd.concat(df_list, ignore_index=True)

    if "technical_score" not in df.columns and "score" in df.columns:
        df["technical_score"] = pd.to_numeric(df["score"], errors="coerce")

    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df["exit_time"] = pd.to_datetime(df["exit_time"], errors="coerce")
    df["entry_day"] = df["entry_time"].dt.day_name()

    numeric_columns = [col for col in OPTIONAL_NUMERIC_COLUMNS if col in df.columns]
    for col in REQUIRED_COLUMNS:
        if col not in {"symbol", "entry_time", "exit_time", "exit_reason", "reasons"}:
            if col in df.columns:
                numeric_columns.append(col)

    numeric_columns = list(dict.fromkeys(numeric_columns))
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    completed_reasons = ["STOP", "TARGET", "DAILY_TP2", "END_OF_BACKTEST", "STOP_AMBIGUOUS_BAR"]
    df = df[df["exit_reason"].isin(completed_reasons)].copy()

    if df.empty:
        return

    df["is_win"] = (df["pnl"] > 0)
    df["is_loss"] = (df["pnl"] < 0)
    df["r_multiple"] = (df["pnl"] / df["risk_amount"].replace(0, pd.NA))

    df["pattern_type"] = "Aucune Formasyon"
    if "reasons" in df.columns:
        df.loc[df["reasons"].str.contains("Çekiç|Hammer", na=False, case=False), "pattern_type"] = "Hammer"
        df.loc[df["reasons"].str.contains("Yutan|Engulfing", na=False, case=False), "pattern_type"] = "Engulfing"
        df.loc[df["reasons"].str.contains("Bayrak|Flag", na=False, case=False), "pattern_type"] = "Bull Flag"

    print_separator()
    print(f"TRADE ANALYTICS REPORT {REPORT_VERSION}")
    print_separator()
    print(f"Trades analysés      : {len(df)}")
    print(f"Trades Gagnants      : {int(df['is_win'].sum())}")
    print(f"Trades Perdants      : {int(df['is_loss'].sum())}")
    print(f"Win Rate             : {calculate_win_rate(df):.2f}%")
    
    break_even_count = len(df[(df["exit_reason"] == "STOP") & (df["r_multiple"] > -0.2) & (df["r_multiple"] < 0.2)])
    print(f"Sorties Break-Even   : {break_even_count} (Pertes totales évitées)")
    print()

    print("[PERFORMANCE GLOBALE]")
    print(f"Profit Brut          : ${safe_sum(df.loc[df['pnl'] > 0, 'pnl']):.4f}")
    print(f"Perte Brute          : ${abs(safe_sum(df.loc[df['pnl'] < 0, 'pnl'])):.4f}")
    pf = calculate_profit_factor(df)
    print(f"Profit Factor        : {pf:.4f}")
    print(f"Total PnL            : ${safe_sum(df['pnl']):.4f}")
    print()

    print("[PERFORMANCE PAR JOUR]")
    print_group_stats(df, "entry_day")
    print()

    if "pattern_type" in df.columns and len(df[df["pattern_type"] != "Aucune Formasyon"]) > 0:
        print("[PERFORMANCE DES PATTERNS]")
        print_group_stats(df, "pattern_type")
        print()

    print("[SYMBOLES]")
    print_group_stats(df, "symbol")
    print()

    generate_ai_insights(df)

if __name__ == "__main__":
    analyze_backtest_data()