from __future__ import annotations
import math
import os
import glob
import pandas as pd

# ============================================================
# CONFIG
# ============================================================
# Klasör adını buraya yazıyoruz (Eğer farklıysa burayı güncelleyin)
CSV_DIR = "old_trade_analytics_csv_file"
REPORT_VERSION = "V2.1-Quant-AI-Folder-Scan"

# ============================================================
# HELPERS
# ============================================================
def print_separator():
    print("=" * 72)

def safe_mean(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return 0.0
    return float(series.mean())

def safe_median(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return 0.0
    return float(series.median())

def safe_sum(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return 0.0
    return float(series.sum())

def calculate_profit_factor(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    profits = pd.to_numeric(df.loc[df["pnl"] > 0, "pnl"], errors="coerce").dropna()
    losses = pd.to_numeric(df.loc[df["pnl"] < 0, "pnl"], errors="coerce").dropna()

    gross_profit = float(profits.sum())
    gross_loss = abs(float(losses.sum()))

    if gross_loss == 0:
        if gross_profit > 0:
            return float("inf")
        return 0.0
    return gross_profit / gross_loss

def calculate_expectancy(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return safe_mean(df["pnl"])

def print_profit_factor(value: float):
    if math.isinf(value):
        print("Profit Factor        : Infinity")
    else:
        print(f"Profit Factor        : {value:.4f}")

def calculate_win_rate(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float(df["is_win"].mean() * 100.0)

# ============================================================
# GROUP ANALYSIS
# ============================================================
def calculate_group_stats(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    if group_column not in df.columns:
        return pd.DataFrame()

    working = df[df[group_column].notna()].copy()
    if working.empty:
        return pd.DataFrame()

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
        print("Veri bulunamadı.")
        return
    print(stats.to_string())

# ============================================================
# REQUIRED COLUMNS
# ============================================================
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
    "alpha_base_score", "alpha_regime_adjustment", "fundamental_data_quality",
    "revenue_growth", "net_income_growth", "eps_growth", "revenue_ttm_growth",
    "net_income_ttm_growth", "eps_ttm_growth", "fcf_ttm_growth", "net_margin",
    "roe", "free_cash_flow_margin", "earnings_quality", "debt_to_assets",
    "cash_to_assets",
]

CATEGORICAL_COLUMNS = [
    "symbol", "exit_reason", "market_regime", "alpha_mode",
    "fundamental_available", "fundamental_data_quality", "reasons"
]

def add_bracket(df: pd.DataFrame, source_column: str, target_column: str, bins, labels):
    if source_column not in df.columns:
        return
    df[target_column] = pd.cut(
        df[source_column], bins=bins, labels=labels, include_lowest=True
    )

# ============================================================
# AI QUANT INSIGHTS GENERATOR
# ============================================================
def generate_ai_insights(df: pd.DataFrame):
    print_separator()
    print("[AI QUANT ASSISTANT - OTOPSİ VE STRATEJİ ÖNERİLERİ]")
    print_separator()
    
    insights = []
    
    win_rate = calculate_win_rate(df)
    pf = calculate_profit_factor(df)
    if win_rate < 40 and pf > 1.5:
        insights.append(f"🟢 [ASİMETRİK KÂR]: Kazanma oranınız düşük ({win_rate:.1f}%) ancak kâr faktörünüz çok güçlü ({pf:.2f}). Zararı kes kuralınız kusursuz çalışıyor, stratejiyi değiştirmeyin.")
    elif win_rate > 50 and pf < 1.0:
        insights.append(f"🔴 [TEHLİKE]: Çok sık kazanıyorsunuz ({win_rate:.1f}%) ancak kâr faktörünüz zayıf ({pf:.2f}). Kayıplarınız kazançlarınızı yutuyor. Stop mesafesini daraltmalısınız.")

    if "entry_day" in df.columns:
        day_stats = calculate_group_stats(df, "entry_day")
        if not day_stats.empty:
            worst_day = day_stats.sort_values("Total_PnL").index[0]
            worst_day_pnl = day_stats.loc[worst_day, "Total_PnL"]
            if worst_day_pnl < 0:
                insights.append(f"🔴 [ZAMANLAMA HATASI]: En çok zararı {worst_day} günü açtığınız işlemlerde (Total PnL: ${worst_day_pnl:.2f}) yaşıyorsunuz. Bu günlerde filtreleri sıkılaştırın veya işlem almamayı düşünün.")
            
            best_day = day_stats.sort_values("Total_PnL", ascending=False).index[0]
            insights.append(f"🟢 [AV GÜNÜ]: Sisteminiz en iyi performansı {best_day} günleri gösteriyor.")

    avg_win_time = safe_mean(df.loc[df["is_win"], "holding_minutes"]) / 1440
    avg_loss_time = safe_mean(df.loc[df["is_loss"], "holding_minutes"]) / 1440
    if avg_loss_time > avg_win_time:
        insights.append(f"🔴 [UMUT ETTİREN ZARARLAR]: Kaybeden işlemlerde (Ort: {avg_loss_time:.1f} gün) kazananlardan (Ort: {avg_win_time:.1f} gün) daha uzun süre kalıyorsunuz. Stopları daha erken tetikleyin.")
    else:
        insights.append(f"🟢 [MÜKEMMEL DİSİPLİN]: Zararı erken kesip (Ort: {avg_loss_time:.1f} gün), kârı sonuna kadar sürüyorsunuz (Ort: {avg_win_time:.1f} gün).")

    if "pattern_type" in df.columns:
        pat_stats = calculate_group_stats(df, "pattern_type")
        if not pat_stats.empty and "Formasyon Yok" in pat_stats.index:
            has_pat = pat_stats[pat_stats.index != "Formasyon Yok"]
            if not has_pat.empty:
                best_pat = has_pat.sort_values("Total_PnL", ascending=False).index[0]
                insights.append(f"🟢 [AVCI GÖZÜ]: '{best_pat}' formasyonunda sistem harika çalışıyor. Formasyonsuz girişleri azaltabilirsiniz.")

    if not insights:
        insights.append("Sistem stabil görünüyor. Belirgin bir anomali tespit edilemedi.")

    for insight in insights:
        print(insight)
    print()

# ============================================================
# MAIN FOLDER SCANNER
# ============================================================
def analyze_backtest_data(csv_dir: str = CSV_DIR):
    if not os.path.exists(csv_dir) or not os.path.isdir(csv_dir):
        print(f"Hata: '{csv_dir}' adında bir klasör bulunamadı.")
        return

    csv_files = glob.glob(os.path.join(csv_dir, "*.csv"))
    
    if not csv_files:
        print(f"Hata: '{csv_dir}' klasörünün içinde hiç CSV dosyası yok.")
        return

    print(f"Veriler yükleniyor... ({len(csv_files)} dosya bulundu)")
    
    df_list = []
    for file in csv_files:
        try:
            temp_df = pd.read_csv(file)
            if not temp_df.empty:
                df_list.append(temp_df)
        except Exception as e:
            print(f"Uyarı: {file} okunamadı. Hata: {e}")

    if not df_list:
        print("Klasördeki dosyaların içi boş veya okunamıyor.")
        return

    df = pd.concat(df_list, ignore_index=True)

    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        print("Eksik zorunlu CSV kolonları (En az bir dosyada bu kolonlar yok):")
        for col in missing_required:
            print(f" - {col}")
        return

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

    if "fundamental_available" in df.columns:
        def normalize_bool(value):
            if pd.isna(value): return pd.NA
            if isinstance(value, bool): return value
            text = str(value).strip().lower()
            if text in {"true", "1", "yes", "available"}: return True
            if text in {"false", "0", "no", "unavailable"}: return False
            return pd.NA
        df["fundamental_available"] = df["fundamental_available"].map(normalize_bool).astype("boolean")

    completed_reasons = ["STOP", "TARGET", "DAILY_TP2", "END_OF_BACKTEST", "STOP_AMBIGUOUS_BAR"]
    df = df[df["exit_reason"].isin(completed_reasons)].copy()

    if df.empty:
        print("Analiz edilecek tamamlanmış işlem bulunamadı.")
        return

    df["is_win"] = (df["pnl"] > 0)
    df["is_loss"] = (df["pnl"] < 0)
    df["is_ambiguous"] = (df["exit_reason"] == "STOP_AMBIGUOUS_BAR")
    df["r_multiple"] = (df["pnl"] / df["risk_amount"].replace(0, pd.NA))
    df["stop_pct_of_entry"] = (df["stop_distance"] / df["entry_price"] * 100.0)
    df["target_pct_of_entry"] = (df["target_distance"] / df["entry_price"] * 100.0)
    df["risk_to_position_value_pct"] = (df["risk_amount"] / df["position_value"] * 100.0)

    if "entry_equity" in df.columns:
        df["risk_to_equity_pct"] = (df["risk_amount"] / df["entry_equity"] * 100.0)
        df["trade_return_on_equity_pct"] = (df["pnl"] / df["entry_equity"] * 100.0)
        df["entry_exposure_pct"] = (df["position_value"] / df["entry_equity"] * 100.0)

    df["overnight"] = (df["entry_time"].dt.date != df["exit_time"].dt.date)

    df["pattern_type"] = "Formasyon Yok"
    if "reasons" in df.columns:
        df.loc[df["reasons"].str.contains("Çekiç|Hammer", na=False, case=False), "pattern_type"] = "Hammer"
        df.loc[df["reasons"].str.contains("Yutan|Engulfing", na=False, case=False), "pattern_type"] = "Engulfing"
        df.loc[df["reasons"].str.contains("Bayrak|Flag", na=False, case=False), "pattern_type"] = "Bull Flag"

    # ========================================================
    # HEADER
    # ========================================================
    print_separator()
    print(f"TRADE ANALYTICS REPORT {REPORT_VERSION}")
    print_separator()
    print(f"Scanned Folder       : {csv_dir} ({len(csv_files)} files)")
    print(f"Analyzed Trades      : {len(df)}")
    print(f"Winning Trades       : {int(df['is_win'].sum())}")
    print(f"Losing Trades        : {int(df['is_loss'].sum())}")
    print(f"Win Rate             : {calculate_win_rate(df):.2f}%")
    
    break_even_count = len(df[(df["exit_reason"] == "STOP") & (df["r_multiple"] > -0.2) & (df["r_multiple"] < 0.2)])
    print(f"Break-Even Exits     : {break_even_count} (Saved from full loss)")
    print()

    # ========================================================
    # OVERALL PERFORMANCE
    # ========================================================
    print("[OVERALL PERFORMANCE]")
    gross_profit = safe_sum(df.loc[df["pnl"] > 0, "pnl"])
    gross_loss = abs(safe_sum(df.loc[df["pnl"] < 0, "pnl"]))
    print(f"Gross Profit         : ${gross_profit:.4f}")
    print(f"Gross Loss           : ${gross_loss:.4f}")
    print_profit_factor(calculate_profit_factor(df))
    print(f"Expectancy / Trade   : ${calculate_expectancy(df):.4f}")
    print(f"Total PnL            : ${safe_sum(df['pnl']):.4f}")
    print(f"Average PnL          : ${safe_mean(df['pnl']):.4f}")
    print(f"Best Trade           : ${df['pnl'].max():.4f}")
    print(f"Worst Trade          : ${df['pnl'].min():.4f}")
    print()

    # ========================================================
    # DAY OF WEEK PERFORMANCE
    # ========================================================
    print("[DAY OF WEEK PERFORMANCE]")
    print_group_stats(df, "entry_day")
    print()

    # ========================================================
    # PATTERN PERFORMANCE
    # ========================================================
    if "pattern_type" in df.columns and len(df[df["pattern_type"] != "Formasyon Yok"]) > 0:
        print("[PATTERN / FORMASYON PERFORMANCE]")
        print_group_stats(df, "pattern_type")
        print()

    # ========================================================
    # R MULTIPLE
    # ========================================================
    print("[R-MULTIPLE]")
    print(f"Average R            : {safe_mean(df['r_multiple']):.4f}R")
    print(f"Best R               : {df['r_multiple'].max():.4f}R")
    print(f"Worst R              : {df['r_multiple'].min():.4f}R")
    print()

    # ========================================================
    # EXIT REASON
    # ========================================================
    print("[EXIT REASON]")
    print_group_stats(df, "exit_reason")
    print()

    # ========================================================
    # SYMBOL PERFORMANCE
    # ========================================================
    print("[SYMBOL PERFORMANCE]")
    print_group_stats(df, "symbol")
    print()

    # ========================================================
    # QUANT AI INSIGHTS
    # ========================================================
    generate_ai_insights(df)

if __name__ == "__main__":
    analyze_backtest_data()