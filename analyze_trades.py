from __future__ import annotations
import math
import pandas as pd

# ============================================================
# CONFIG
# ============================================================
CSV_FILE = "trade_analytics.csv"
REPORT_VERSION = "V1.8"

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

    profits = pd.to_numeric(
        df.loc[df["pnl"] > 0, "pnl"],
        errors="coerce",
    ).dropna()

    losses = pd.to_numeric(
        df.loc[df["pnl"] < 0, "pnl"],
        errors="coerce",
    ).dropna()

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

        print(
            "Profit Factor        : Infinity"
        )

    else:

        print(
            f"Profit Factor        : "
            f"{value:.4f}"
        )

def calculate_win_rate(df: pd.DataFrame) -> float:

    if df.empty:
        return 0.0

    return float(
        df["is_win"].mean() * 100.0
    )

def calculate_return_pct(
    pnl: float,
    equity: float,
) -> float:
    if equity is None:
        return 0.0

    if pd.isna(equity):
        return 0.0

    if equity == 0:
        return 0.0

    return float(
        pnl / equity * 100.0
    )

# ============================================================
# GROUP ANALYSIS
# ============================================================
def calculate_group_stats(
    df: pd.DataFrame,
    group_column: str,
) -> pd.DataFrame:
    if group_column not in df.columns:
        return pd.DataFrame()

    working = df[
        df[group_column].notna()
    ].copy()

    if working.empty:
        return pd.DataFrame()

    result = (
        working.groupby(
            group_column,
            observed=False,
            dropna=False,
        )
        .agg(
            Total_Trades=(
                "pnl",
                "count",
            ),
            Win_Rate=(
                "is_win",
                lambda x: x.mean() * 100.0,
            ),
            Total_PnL=(
                "pnl",
                "sum",
            ),
            Average_PnL=(
                "pnl",
                "mean",
            ),
            Average_R=(
                "r_multiple",
                "mean",
            ),
        )
        .sort_values(
            "Total_PnL",
            ascending=False,
        )
        .round(4)
    )

    return result

def print_group_stats(
    df: pd.DataFrame,
    group_column: str,
):
    stats = calculate_group_stats(
        df,
        group_column,
    )

    if stats.empty:

        print(
            "Veri bulunamadı."
        )

        return

    print(
        stats.to_string()
    )

# ============================================================
# REQUIRED COLUMNS
# ============================================================
REQUIRED_COLUMNS = [

    "symbol",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "quantity",
    "pnl",
    "pnl_pct",
    "exit_reason",

    "rsi",
    "volume_ratio",
    "atr",

    "stop_distance",
    "target_distance",

    "risk_reward_ratio",

    "position_value",
    "risk_amount",

    "holding_minutes",
]

# ============================================================
# OPTIONAL / V1.8 COLUMNS
# ============================================================
OPTIONAL_NUMERIC_COLUMNS = [

    # Execution
    "gross_pnl",
    "entry_value",
    "exit_value",
    "return_on_entry_pct",

    # Core risk / portfolio
    "entry_equity",
    "exposure_pct",
    "max_total_open_risk",
    "projected_open_risk",

    # Scores
    "signal_score",
    "technical_score",
    "fundamental_score",
    "alpha_score",
    "alpha_base_score",
    "alpha_regime_adjustment",

    # Fundamental quality
    "fundamental_data_quality",

    # Fundamental raw factors
    "revenue_growth",
    "net_income_growth",
    "eps_growth",

    "revenue_ttm_growth",
    "net_income_ttm_growth",
    "eps_ttm_growth",
    "fcf_ttm_growth",

    "net_margin",
    "roe",
    "free_cash_flow_margin",
    "earnings_quality",

    "debt_to_assets",
    "cash_to_assets",
]
CATEGORICAL_COLUMNS = [

    "symbol",
    "exit_reason",

    "market_regime",
    "alpha_mode",

    "fundamental_available",
    "fundamental_data_quality",
]

# ============================================================
# BRACKET HELPERS
# ============================================================
def add_bracket(
    df: pd.DataFrame,
    source_column: str,
    target_column: str,
    bins,
    labels,
):
    if source_column not in df.columns:
        return

    df[target_column] = pd.cut(
        df[source_column],
        bins=bins,
        labels=labels,
        include_lowest=True,
    )

# ============================================================
# MAIN
# ============================================================
def analyze_backtest_data(
    csv_file: str = CSV_FILE,
):
    # ========================================================
    # LOAD CSV
    # ========================================================

    try:

        df = pd.read_csv(
            csv_file
        )

    except FileNotFoundError:

        print(
            f"Hata: {csv_file} bulunamadı. "
            "Önce backtest'i çalıştırın."
        )

        return

    if df.empty:

        print(
            "Analiz edilecek işlem bulunamadı."
        )

        return

    # ========================================================
    # REQUIRED COLUMN CHECK
    # ========================================================

    missing_required = [

        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns

    ]

    if missing_required:

        print(
            "Eksik zorunlu CSV kolonları:"
        )

        for column in missing_required:

            print(
                f" - {column}"
            )

        return

    # ========================================================
    # BACKWARD COMPATIBILITY
    # ========================================================

    if (
        "technical_score" not in df.columns
        and "score" in df.columns
    ):

        df["technical_score"] = pd.to_numeric(
            df["score"],
            errors="coerce",
        )

    # ========================================================
    # DATE CONVERSION
    # ========================================================

    df["entry_time"] = pd.to_datetime(
        df["entry_time"],
        errors="coerce",
    )

    df["exit_time"] = pd.to_datetime(
        df["exit_time"],
        errors="coerce",
    )

    # ========================================================
    # NUMERIC CONVERSION
    #
    # IMPORTANT:
    # Categorical fields such as market_regime,
    # alpha_mode and fundamental_available are NOT included.
    # ========================================================

    numeric_columns = [
        column
        for column in OPTIONAL_NUMERIC_COLUMNS
        if column in df.columns
    ]

    for column in REQUIRED_COLUMNS:

        if column in {
            "symbol",
            "entry_time",
            "exit_time",
            "exit_reason",
        }:
            continue

        if column in df.columns:
            numeric_columns.append(column)

    numeric_columns = list(
        dict.fromkeys(numeric_columns)
    )

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # ========================================================
    # CATEGORICAL CLEANUP
    # ========================================================

    for column in [
        "symbol",
        "exit_reason",
        "market_regime",
        "alpha_mode",
    ]:

        if column in df.columns:

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    # Fundamental availability can arrive as
    # boolean / string / numeric depending on CSV generation.

    if "fundamental_available" in df.columns:

        def normalize_bool(value):

            if pd.isna(value):
                return pd.NA

            if isinstance(value, bool):
                return value

            text = str(value).strip().lower()

            if text in {
                "true",
                "1",
                "yes",
                "available",
            }:
                return True

            if text in {
                "false",
                "0",
                "no",
                "unavailable",
            }:
                return False

            return pd.NA

        df["fundamental_available"] = (
            df["fundamental_available"]
            .map(normalize_bool)
            .astype("boolean")
        )

    # ========================================================
    # COMPLETED TRADES
    # ========================================================

    completed_reasons = [

        "STOP",
        "TARGET",
        "DAILY_TP2",
        "END_OF_BACKTEST",
        "STOP_AMBIGUOUS_BAR",

    ]

    df = df[
        df["exit_reason"].isin(
            completed_reasons
        )
    ].copy()

    if df.empty:

        print(
            "Analiz edilecek tamamlanmış işlem bulunamadı."
        )

        return

    # ========================================================
    # DERIVED METRICS
    # ========================================================

    df["is_win"] = (
        df["pnl"] > 0
    )

    df["is_loss"] = (
        df["pnl"] < 0
    )

    df["is_ambiguous"] = (
        df["exit_reason"]
        == "STOP_AMBIGUOUS_BAR"
    )

    # ========================================================
    # R MULTIPLE
    # ========================================================

    df["r_multiple"] = (
        df["pnl"]
        / df["risk_amount"]
        .replace(0, pd.NA)
    )

    # ========================================================
    # STOP DISTANCE %
    # ========================================================

    df["stop_pct_of_entry"] = (
        df["stop_distance"]
        / df["entry_price"]
        * 100.0
    )

    # ========================================================
    # TARGET DISTANCE %
    # ========================================================

    df["target_pct_of_entry"] = (
        df["target_distance"]
        / df["entry_price"]
        * 100.0
    )

    # ========================================================
    # RISK / POSITION %
    # ========================================================

    df["risk_to_position_value_pct"] = (
        df["risk_amount"]
        / df["position_value"]
        * 100.0
    )

    # ========================================================
    # REAL ACCOUNT RISK %
    #
    # risk_amount / entry_equity
    # ========================================================

    if "entry_equity" in df.columns:

        df["risk_to_equity_pct"] = (
            df["risk_amount"]
            / df["entry_equity"]
            * 100.0
        )

        df["trade_return_on_equity_pct"] = (
            df["pnl"]
            / df["entry_equity"]
            * 100.0
        )

    # ========================================================
    # EXPOSURE / ENTRY VALUE
    # ========================================================

    if "entry_equity" in df.columns:

        df["entry_exposure_pct"] = (
            df["position_value"]
            / df["entry_equity"]
            * 100.0
        )

    # ========================================================
    # OVERNIGHT
    # ========================================================

    df["overnight"] = (
        df["entry_time"].dt.date
        != df["exit_time"].dt.date
    )

    # ========================================================
    # HEADER
    # ========================================================

    print_separator()

    print(
        f"TRADE ANALYTICS REPORT {REPORT_VERSION}"
    )

    print_separator()

    print(
        f"CSV File             : "
        f"{csv_file}"
    )

    print(
        f"Analyzed Trades      : "
        f"{len(df)}"
    )

    print(
        f"Winning Trades       : "
        f"{int(df['is_win'].sum())}"
    )

    print(
        f"Losing Trades        : "
        f"{int(df['is_loss'].sum())}"
    )

    print(
        f"Win Rate             : "
        f"{calculate_win_rate(df):.2f}%"
    )

    print(
        f"Ambiguous Trades     : "
        f"{int(df['is_ambiguous'].sum())}"
    )

    print(
        f"Overnight Trades     : "
        f"{int(df['overnight'].sum())}"
    )

    print()

    # ========================================================
    # OVERALL PERFORMANCE
    # ========================================================

    print(
        "[OVERALL PERFORMANCE]"
    )

    gross_profit = safe_sum(
        df.loc[
            df["pnl"] > 0,
            "pnl",
        ]
    )

    gross_loss = abs(
        safe_sum(
            df.loc[
                df["pnl"] < 0,
                "pnl",
            ]
        )
    )

    print(
        f"Gross Profit         : "
        f"${gross_profit:.4f}"
    )

    print(
        f"Gross Loss           : "
        f"${gross_loss:.4f}"
    )

    profit_factor = (
        calculate_profit_factor(df)
    )

    print_profit_factor(
        profit_factor
    )

    expectancy = (
        calculate_expectancy(df)
    )

    print(
        f"Expectancy / Trade   : "
        f"${expectancy:.4f}"
    )

    total_pnl = safe_sum(
        df["pnl"]
    )

    print(
        f"Total PnL            : "
        f"${total_pnl:.4f}"
    )

    print(
        f"Average PnL          : "
        f"${safe_mean(df['pnl']):.4f}"
    )

    print(
        f"Median PnL           : "
        f"${safe_median(df['pnl']):.4f}"
    )

    print(
        f"Best Trade           : "
        f"${df['pnl'].max():.4f}"
    )

    print(
        f"Worst Trade          : "
        f"${df['pnl'].min():.4f}"
    )

    # ========================================================
    # ACCOUNT LEVEL RETURN
    # ========================================================

    if "entry_equity" in df.columns:

        valid_equity = df[
            df["entry_equity"].notna()
            & (df["entry_equity"] > 0)
        ]

        if not valid_equity.empty:

            print(
                f"Avg Trade / Equity   : "
                f"{safe_mean(valid_equity['trade_return_on_equity_pct']):.4f}%"
            )

            print(
                f"Median / Equity      : "
                f"{safe_median(valid_equity['trade_return_on_equity_pct']):.4f}%"
            )

    print()

    # ========================================================
    # R MULTIPLE
    # ========================================================

    print(
        "[R-MULTIPLE]"
    )

    print(
        f"Average R            : "
        f"{safe_mean(df['r_multiple']):.4f}R"
    )

    print(
        f"Median R             : "
        f"{safe_median(df['r_multiple']):.4f}R"
    )

    print(
        f"Best R               : "
        f"{df['r_multiple'].max():.4f}R"
    )

    print(
        f"Worst R              : "
        f"{df['r_multiple'].min():.4f}R"
    )

    print()

    # ========================================================
    # RISK STATISTICS
    # ========================================================

    print(
        "[RISK STATISTICS]"
    )

    print(
        f"Average Risk         : "
        f"${safe_mean(df['risk_amount']):.4f}"
    )

    print(
        f"Median Risk          : "
        f"${safe_median(df['risk_amount']):.4f}"
    )

    print(
        f"Maximum Risk         : "
        f"${df['risk_amount'].max():.4f}"
    )

    print(
        f"Minimum Risk         : "
        f"${df['risk_amount'].min():.4f}"
    )

    print(
        f"Avg Risk/Position    : "
        f"{safe_mean(df['risk_to_position_value_pct']):.4f}%"
    )

    print(
        f"Avg Stop Distance    : "
        f"{safe_mean(df['stop_pct_of_entry']):.4f}%"
    )

    print(
        f"Avg Target Distance  : "
        f"{safe_mean(df['target_pct_of_entry']):.4f}%"
    )

    if "risk_to_equity_pct" in df.columns:

        print(
            f"Avg Risk / Equity    : "
            f"{safe_mean(df['risk_to_equity_pct']):.4f}%"
        )

        print(
            f"Median Risk / Equity : "
            f"{safe_median(df['risk_to_equity_pct']):.4f}%"
        )

        print(
            f"Max Risk / Equity    : "
            f"{df['risk_to_equity_pct'].max():.4f}%"
        )

    if "entry_exposure_pct" in df.columns:

        print(
            f"Avg Exposure / Equity: "
            f"{safe_mean(df['entry_exposure_pct']):.4f}%"
        )

        print(
            f"Max Exposure / Equity: "
            f"{df['entry_exposure_pct'].max():.4f}%"
        )

    print()

    # ========================================================
    # HOLDING TIME
    # ========================================================

    print(
        "[HOLDING TIME]"
    )

    print(
        f"Average Holding      : "
        f"{safe_mean(df['holding_minutes']):.2f} min"
    )

    print(
        f"Median Holding       : "
        f"{safe_median(df['holding_minutes']):.2f} min"
    )

    print(
        f"Maximum Holding      : "
        f"{df['holding_minutes'].max():.2f} min"
    )

    print(
        f"Minimum Holding      : "
        f"{df['holding_minutes'].min():.2f} min"
    )

    winning_holding = df.loc[
        df["is_win"],
        "holding_minutes",
    ]

    losing_holding = df.loc[
        df["is_loss"],
        "holding_minutes",
    ]

    print(
        f"Avg Winning Hold     : "
        f"{safe_mean(winning_holding):.2f} min"
    )

    print(
        f"Avg Losing Hold      : "
        f"{safe_mean(losing_holding):.2f} min"
    )

    print()

    # ========================================================
    # EXIT REASON
    # ========================================================

    print(
        "[EXIT REASON]"
    )

    exit_stats = (
        df.groupby(
            "exit_reason",
            observed=False,
        )
        .agg(
            Total_Trades=(
                "pnl",
                "count",
            ),
            Win_Rate=(
                "is_win",
                lambda x: x.mean() * 100.0,
            ),
            Total_PnL=(
                "pnl",
                "sum",
            ),
            Average_PnL=(
                "pnl",
                "mean",
            ),
            Average_R=(
                "r_multiple",
                "mean",
            ),
            Average_Holding=(
                "holding_minutes",
                "mean",
            ),
        )
        .sort_values(
            "Total_PnL",
            ascending=False,
        )
        .round(4)
    )

    print(
        exit_stats.to_string()
    )

    print()

    # ========================================================
    # SYMBOL PERFORMANCE
    # ========================================================

    print(
        "[SYMBOL PERFORMANCE]"
    )

    symbol_stats = (
        df.groupby(
            "symbol",
            observed=False,
        )
        .agg(
            Total_Trades=(
                "pnl",
                "count",
            ),
            Win_Rate=(
                "is_win",
                lambda x: x.mean() * 100.0,
            ),
            Total_PnL=(
                "pnl",
                "sum",
            ),
            Average_PnL=(
                "pnl",
                "mean",
            ),
            Average_R=(
                "r_multiple",
                "mean",
            ),
            Profit_Factor=(
                "pnl",
                lambda x: (
                    x[x > 0].sum()
                    / abs(x[x < 0].sum())
                    if abs(x[x < 0].sum()) > 0
                    else (
                        float("inf")
                        if x[x > 0].sum() > 0
                        else 0.0
                    )
                ),
            ),
            Average_Holding=(
                "holding_minutes",
                "mean",
            ),
        )
        .sort_values(
            "Total_PnL",
            ascending=False,
        )
        .round(4)
    )

    print(
        symbol_stats.to_string()
    )

    print()

    # ========================================================
    # TECHNICAL SCORE
    # ========================================================

    if "technical_score" in df.columns:

        print(
            "[TECHNICAL SCORE PERFORMANCE]"
        )

        add_bracket(
            df,
            "technical_score",
            "technical_bracket",
            [
                -float("inf"),
                59.9999,
                69.9999,
                79.9999,
                89.9999,
                float("inf"),
            ],
            [
                "<60",
                "60-69",
                "70-79",
                "80-89",
                "90+",
            ],
        )

        print_group_stats(
            df,
            "technical_bracket",
        )

        print()

    # ========================================================
    # FUNDAMENTAL SCORE
    # ========================================================

    if "fundamental_score" in df.columns:

        print(
            "[FUNDAMENTAL SCORE PERFORMANCE]"
        )

        add_bracket(
            df,
            "fundamental_score",
            "fundamental_bracket",
            [
                -float("inf"),
                39.9999,
                59.9999,
                69.9999,
                79.9999,
                89.9999,
                float("inf"),
            ],
            [
                "<40",
                "40-59",
                "60-69",
                "70-79",
                "80-89",
                "90+",
            ],
        )

        print_group_stats(
            df,
            "fundamental_bracket",
        )

        print()

    # ========================================================
    # ALPHA SCORE
    # ========================================================

    if "alpha_score" in df.columns:

        print(
            "[COMBINED ALPHA SCORE PERFORMANCE]"
        )

        add_bracket(
            df,
            "alpha_score",
            "alpha_bracket",
            [
                -float("inf"),
                59.9999,
                69.9999,
                79.9999,
                89.9999,
                float("inf"),
            ],
            [
                "<60",
                "60-69",
                "70-79",
                "80-89",
                "90+",
            ],
        )

        print_group_stats(
            df,
            "alpha_bracket",
        )

        print()

    # ========================================================
    # SIGNAL SCORE
    # ========================================================

    if "signal_score" in df.columns:

        print(
            "[SIGNAL SCORE PERFORMANCE]"
        )

        add_bracket(
            df,
            "signal_score",
            "signal_bracket",
            [
                -float("inf"),
                59.9999,
                69.9999,
                79.9999,
                89.9999,
                float("inf"),
            ],
            [
                "<60",
                "60-69",
                "70-79",
                "80-89",
                "90+",
            ],
        )

        print_group_stats(
            df,
            "signal_bracket",
        )

        print()

    # ========================================================
    # TECHNICAL x FUNDAMENTAL
    # ========================================================

    if (
        "technical_score" in df.columns
        and
        "fundamental_score" in df.columns
    ):

        print(
            "[TECHNICAL x FUNDAMENTAL]"
        )

        add_bracket(
            df,
            "technical_score",
            "technical_quality",
            [
                -float("inf"),
                79.9999,
                89.9999,
                float("inf"),
            ],
            [
                "Technical <80",
                "Technical 80-89",
                "Technical 90+",
            ],
        )

        add_bracket(
            df,
            "fundamental_score",
            "fundamental_quality",
            [
                -float("inf"),
                59.9999,
                79.9999,
                float("inf"),
            ],
            [
                "Fundamental <60",
                "Fundamental 60-79",
                "Fundamental 80+",
            ],
        )

        df["factor_quadrant"] = (
            df["technical_quality"].astype("string")
            + " | "
            + df["fundamental_quality"].astype("string")
        )

        print_group_stats(
            df,
            "factor_quadrant",
        )

        print()

    # ========================================================
    # HIGH ALPHA / HIGH FUNDAMENTAL
    # ========================================================

    if (
        "alpha_score" in df.columns
        and
        "fundamental_score" in df.columns
    ):

        print(
            "[HIGH-QUALITY ALPHA FILTERS]"
        )

        high_alpha = df[
            df["alpha_score"] >= 90
        ]

        high_fundamental = df[
            df["fundamental_score"] >= 80
        ]

        high_both = df[
            (
                df["alpha_score"] >= 90
            )
            &
            (
                df["fundamental_score"] >= 80
            )
        ]

        print(
            f"Alpha >= 90          : "
            f"{len(high_alpha)} trades | "
            f"Win {calculate_win_rate(high_alpha):.2f}% | "
            f"PnL ${safe_sum(high_alpha['pnl']):.4f} | "
            f"Avg R {safe_mean(high_alpha['r_multiple']):.4f}"
        )

        print(
            f"Fundamental >= 80    : "
            f"{len(high_fundamental)} trades | "
            f"Win {calculate_win_rate(high_fundamental):.2f}% | "
            f"PnL ${safe_sum(high_fundamental['pnl']):.4f} | "
            f"Avg R {safe_mean(high_fundamental['r_multiple']):.4f}"
        )

        print(
            f"Alpha >= 90 AND "
            f"Fundamental >= 80   : "
            f"{len(high_both)} trades | "
            f"Win {calculate_win_rate(high_both):.2f}% | "
            f"PnL ${safe_sum(high_both['pnl']):.4f} | "
            f"Avg R {safe_mean(high_both['r_multiple']):.4f} | "
            f"PF {calculate_profit_factor(high_both):.4f}"
        )

        print()

    # ========================================================
    # MARKET REGIME
    # ========================================================

    if "market_regime" in df.columns:

        print(
            "[MARKET REGIME PERFORMANCE]"
        )

        print_group_stats(
            df,
            "market_regime",
        )

        print()

    # ========================================================
    # ALPHA MODE
    # ========================================================

    if "alpha_mode" in df.columns:

        print(
            "[ALPHA MODE PERFORMANCE]"
        )

        print_group_stats(
            df,
            "alpha_mode",
        )

        print()

    # ========================================================
    # FUNDAMENTAL AVAILABILITY
    # ========================================================

    if "fundamental_available" in df.columns:

        print(
            "[FUNDAMENTAL AVAILABILITY]"
        )

        print_group_stats(
            df,
            "fundamental_available",
        )

        print()

    # ========================================================
    # ALPHA REGIME ADJUSTMENT
    # ========================================================

    if "alpha_regime_adjustment" in df.columns:

        print(
            "[ALPHA REGIME ADJUSTMENT]"
        )

        print_group_stats(
            df,
            "alpha_regime_adjustment",
        )

        print()

    # ========================================================
    # FUNDAMENTAL DATA QUALITY
    # ========================================================

    if "fundamental_data_quality" in df.columns:

        print(
            "[FUNDAMENTAL DATA QUALITY]"
        )

        add_bracket(
            df,
            "fundamental_data_quality",
            "fundamental_quality_bracket",
            [
                -float("inf"),
                59.9999,
                79.9999,
                89.9999,
                float("inf"),
            ],
            [
                "<60",
                "60-79",
                "80-89",
                "90+",
            ],
        )

        print_group_stats(
            df,
            "fundamental_quality_bracket",
        )

        print()

    # ========================================================
    # GROWTH FACTORS
    # ========================================================

    growth_columns = [

        (
            "revenue_growth",
            "REVENUE GROWTH",
        ),

        (
            "net_income_growth",
            "NET INCOME GROWTH",
        ),

        (
            "eps_growth",
            "EPS GROWTH",
        ),

        (
            "revenue_ttm_growth",
            "REVENUE TTM GROWTH",
        ),

        (
            "net_income_ttm_growth",
            "NET INCOME TTM GROWTH",
        ),

        (
            "eps_ttm_growth",
            "EPS TTM GROWTH",
        ),

        (
            "fcf_ttm_growth",
            "FCF TTM GROWTH",
        ),

    ]

    for column, title in growth_columns:

        if column not in df.columns:
            continue

        print(
            f"[{title} PERFORMANCE]"
        )

        add_bracket(
            df,
            column,
            f"{column}_bracket",
            [
                -float("inf"),
                -0.05,
                0.00,
                0.10,
                0.20,
                float("inf"),
            ],
            [
                "<-5%",
                "-5%-0%",
                "0%-10%",
                "10%-20%",
                "20%+",
            ],
        )

        print_group_stats(
            df,
            f"{column}_bracket",
        )

        print()

    # ========================================================
    # PROFITABILITY
    # ========================================================

    profitability_columns = [

        (
            "net_margin",
            "NET MARGIN",
        ),

        (
            "roe",
            "ROE",
        ),

        (
            "free_cash_flow_margin",
            "FCF MARGIN",
        ),

    ]

    profitability_bins = [
        -float("inf"),
        0.00,
        0.10,
        0.20,
        0.30,
        float("inf"),
    ]

    profitability_labels = [
        "<0%",
        "0%-10%",
        "10%-20%",
        "20%-30%",
        "30%+",
    ]

    for column, title in profitability_columns:

        if column not in df.columns:
            continue

        print(
            f"[{title} PERFORMANCE]"
        )

        add_bracket(
            df,
            column,
            f"{column}_bracket",
            profitability_bins,
            profitability_labels,
        )

        print_group_stats(
            df,
            f"{column}_bracket",
        )

        print()

    # ========================================================
    # BALANCE SHEET
    # ========================================================

    balance_columns = [

        (
            "debt_to_assets",
            "DEBT / ASSETS",
            [
                -float("inf"),
                0.30,
                0.50,
                0.70,
                0.90,
                float("inf"),
            ],
            [
                "<30%",
                "30%-50%",
                "50%-70%",
                "70%-90%",
                "90%+",
            ],
        ),

        (
            "cash_to_assets",
            "CASH / ASSETS",
            [
                -float("inf"),
                0.05,
                0.10,
                0.20,
                0.30,
                float("inf"),
            ],
            [
                "<5%",
                "5%-10%",
                "10%-20%",
                "20%-30%",
                "30%+",
            ],
        ),

    ]

    for (
        column,
        title,
        bins,
        labels,
    ) in balance_columns:

        if column not in df.columns:
            continue

        print(
            f"[{title} PERFORMANCE]"
        )

        add_bracket(
            df,
            column,
            f"{column}_bracket",
            bins,
            labels,
        )

        print_group_stats(
            df,
            f"{column}_bracket",
        )

        print()

    # ========================================================
    # RSI
    # ========================================================

    print(
        "[RSI PERFORMANCE]"
    )

    add_bracket(
        df,
        "rsi",
        "rsi_bracket",
        [
            -float("inf"),
            55,
            65,
            float("inf"),
        ],
        [
            "<55",
            "55-65",
            ">65",
        ],
    )

    print_group_stats(
        df,
        "rsi_bracket",
    )

    print()

    # ========================================================
    # VOLUME
    # ========================================================

    print(
        "[VOLUME PERFORMANCE]"
    )

    add_bracket(
        df,
        "volume_ratio",
        "volume_bracket",
        [
            -float("inf"),
            1.0,
            2.0,
            float("inf"),
        ],
        [
            "<1.0",
            "1.0-2.0",
            ">2.0",
        ],
    )

    print_group_stats(
        df,
        "volume_bracket",
    )

    print()

    # ========================================================
    # OVERNIGHT
    # ========================================================

    print(
        "[OVERNIGHT PERFORMANCE]"
    )

    print_group_stats(
        df,
        "overnight",
    )

    print()

    # ========================================================
    # TOP 5 WINNERS
    # ========================================================

    print(
        "[TOP 5 WINNING TRADES]"
    )

    winner_columns = [

        "symbol",
        "entry_time",
        "exit_time",

        "pnl",
        "r_multiple",

        "holding_minutes",
        "exit_reason",

    ]

    optional_winner_columns = [

        "signal_score",
        "technical_score",
        "fundamental_score",
        "alpha_score",
        "alpha_base_score",
        "alpha_regime_adjustment",
        "market_regime",
        "alpha_mode",
        "fundamental_data_quality",
        "entry_equity",
        "risk_amount",
        "risk_to_equity_pct",

    ]

    winner_columns.extend(
        column
        for column in optional_winner_columns
        if column in df.columns
    )

    best_trades = (
        df.nlargest(
            5,
            "pnl",
        )[winner_columns]
    )

    print(
        best_trades.to_string(
            index=False
        )
    )

    print()

    # ========================================================
    # TOP 5 LOSERS
    # ========================================================

    print(
        "[TOP 5 LOSING TRADES]"
    )

    loser_columns = [

        "symbol",
        "entry_time",
        "exit_time",

        "pnl",
        "r_multiple",

        "holding_minutes",
        "exit_reason",

    ]

    loser_columns.extend(
        column
        for column in optional_winner_columns
        if column in df.columns
    )

    worst_trades = (
        df.nsmallest(
            5,
            "pnl",
        )[loser_columns]
    )

    print(
        worst_trades.to_string(
            index=False
        )
    )

    print()

    # ========================================================
    # DATA QUALITY
    # ========================================================

    print(
        "[DATA QUALITY CHECK]"
    )

    print(
        f"Rows Analysed        : "
        f"{len(df)}"
    )

    print(
        f"Missing Entry Time   : "
        f"{df['entry_time'].isna().sum()}"
    )

    print(
        f"Missing Exit Time    : "
        f"{df['exit_time'].isna().sum()}"
    )

    print(
        f"Missing Risk         : "
        f"{df['risk_amount'].isna().sum()}"
    )

    print(
        f"Missing RSI          : "
        f"{df['rsi'].isna().sum()}"
    )

    print(
        f"Missing Volume       : "
        f"{df['volume_ratio'].isna().sum()}"
    )

    # ========================================================
    # V1.8 ALPHA DATA AVAILABILITY
    # ========================================================

    print()

    print(
        "[V1.8 ALPHA DATA AVAILABILITY]"
    )

    alpha_columns = [

        "technical_score",
        "fundamental_score",
        "alpha_score",
        "alpha_base_score",
        "alpha_regime_adjustment",

        "market_regime",
        "alpha_mode",

        "fundamental_available",
        "fundamental_data_quality",

        "entry_equity",
        "exposure_pct",
        "projected_open_risk",

    ]

    available_alpha_columns = [
        column
        for column in alpha_columns
        if column in df.columns
    ]

    for column in available_alpha_columns:

        available = int(
            df[column].notna().sum()
        )

        print(
            f" - {column:<28} "
            f"{available}/{len(df)} "
            f"available"
        )

    missing_alpha_columns = [
        column
        for column in alpha_columns
        if column not in df.columns
    ]

    if missing_alpha_columns:

        print()

        print(
            "Missing V1.8 columns:"
        )

        for column in missing_alpha_columns:

            print(
                f" - {column}"
            )

    # ========================================================
    # ALPHA CONSISTENCY CHECK
    # ========================================================

    if {
        "technical_score",
        "fundamental_score",
        "alpha_score",
        "alpha_base_score",
        "alpha_regime_adjustment",
    }.issubset(df.columns):

        print()

        print(
            "[ALPHA FORMULA VALIDATION]"
        )

        multi_factor = df[
            df["fundamental_score"].notna()
        ].copy()

        if not multi_factor.empty:

            multi_factor["expected_base"] = (
                multi_factor["technical_score"] * 0.65
                +
                multi_factor["fundamental_score"] * 0.35
            )

            multi_factor["expected_alpha"] = (
                multi_factor["expected_base"]
                +
                multi_factor["alpha_regime_adjustment"]
            )

            base_error = (
                multi_factor["alpha_base_score"]
                -
                multi_factor["expected_base"]
            ).abs()

            final_error = (
                multi_factor["alpha_score"]
                -
                multi_factor["expected_alpha"]
            ).abs()

            print(
                f"Multi-Factor Trades  : "
                f"{len(multi_factor)}"
            )

            print(
                f"Max Base Error       : "
                f"{safe_mean(base_error):.8f} avg / "
                f"{base_error.max():.8f} max"
            )

            print(
                f"Max Final Error      : "
                f"{safe_mean(final_error):.8f} avg / "
                f"{final_error.max():.8f} max"
            )

        else:

            print(
                "Multi-factor alpha verisi bulunamadı."
            )

    # ========================================================
    # FUNDAMENTAL FALLBACK / MULTI-FACTOR COUNTS
    # ========================================================

    if "alpha_mode" in df.columns:

        print()

        print(
            "[ALPHA MODE COUNTS]"
        )

        mode_counts = (
            df["alpha_mode"]
            .value_counts(dropna=False)
        )

        for mode, count in mode_counts.items():

            print(
                f" - {mode}: {count}"
            )

    # ========================================================
    # MARKET REGIME COUNTS
    # ========================================================

    if "market_regime" in df.columns:

        print()

        print(
            "[MARKET REGIME COUNTS]"
        )

        regime_counts = (
            df["market_regime"]
            .value_counts(dropna=False)
        )

        for regime, count in regime_counts.items():

            print(
                f" - {regime}: {count}"
            )

    # ========================================================
    # REAL ACCOUNT RISK VALIDATION
    # ========================================================

    print()

    print(
        "[ACCOUNT RISK VALIDATION]"
    )

    if "entry_equity" in df.columns:

        valid_risk = df[
            df["entry_equity"].notna()
            &
            (df["entry_equity"] > 0)
        ].copy()

        if not valid_risk.empty:

            valid_risk["risk_pct"] = (
                valid_risk["risk_amount"]
                /
                valid_risk["entry_equity"]
                * 100.0
            )

            print(
                f"Trades with Equity  : "
                f"{len(valid_risk)}/{len(df)}"
            )

            print(
                f"Average Risk %      : "
                f"{safe_mean(valid_risk['risk_pct']):.4f}%"
            )

            print(
                f"Median Risk %       : "
                f"{safe_median(valid_risk['risk_pct']):.4f}%"
            )

            print(
                f"Maximum Risk %      : "
                f"{valid_risk['risk_pct'].max():.4f}%"
            )

            print(
                f"Minimum Risk %      : "
                f"{valid_risk['risk_pct'].min():.4f}%"
            )

            # Compare with configured 1% maximum
            above_1pct = (
                valid_risk["risk_pct"] > 1.0
            )

            print(
                f"Risk > 1.00%        : "
                f"{int(above_1pct.sum())} trades"
            )

        else:

            print(
                "Geçerli entry_equity verisi bulunamadı."
            )

    else:

        print(
            "entry_equity CSV'de bulunamadı."
        )

    # ========================================================
    # FINAL INTERPRETATION
    # ========================================================

    print()

    print(
        "[QUANT INTERPRETATION]"
    )

    if "alpha_score" in df.columns:

        alpha_high = df[
            df["alpha_score"] >= 90
        ]

        print(
            f"Alpha >= 90          : "
            f"{len(alpha_high)} trades | "
            f"Win {calculate_win_rate(alpha_high):.2f}% | "
            f"PnL ${safe_sum(alpha_high['pnl']):.4f} | "
            f"Avg R {safe_mean(alpha_high['r_multiple']):.4f}"
        )

    else:

        print(
            "Alpha score analizi CSV'de mevcut değil."
        )

    if "fundamental_score" in df.columns:

        fundamental_high = df[
            df["fundamental_score"] >= 80
        ]

        print(
            f"Fundamental >= 80    : "
            f"{len(fundamental_high)} trades | "
            f"Win {calculate_win_rate(fundamental_high):.2f}% | "
            f"PnL ${safe_sum(fundamental_high['pnl']):.4f} | "
            f"Avg R {safe_mean(fundamental_high['r_multiple']):.4f}"
        )

    else:

        print(
            "Fundamental score analizi CSV'de mevcut değil."
        )

    if (
        "alpha_score" in df.columns
        and
        "fundamental_score" in df.columns
    ):

        strongest = df[
            (
                df["alpha_score"] >= 90
            )
            &
            (
                df["fundamental_score"] >= 80
            )
        ]

        if not strongest.empty:

            print(
                f"Alpha >=90 + "
                f"Fundamental >=80: "
                f"{len(strongest)} trades | "
                f"Win {calculate_win_rate(strongest):.2f}% | "
                f"PnL ${safe_sum(strongest['pnl']):.4f} | "
                f"PF {calculate_profit_factor(strongest):.4f} | "
                f"Avg R {safe_mean(strongest['r_multiple']):.4f}"
            )

        else:

            print(
                "Alpha >=90 + Fundamental >=80: "
                "uygun trade yok."
            )

    # ========================================================
    # FINAL
    # ========================================================

    print_separator()

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    analyze_backtest_data()