from pathlib import Path

import pandas as pd

from config.settings import load_settings
from data.market_data import MarketData
from backtest.engine import (
    BacktestEngine,
    BacktestConfig,
)
from backtest.metrics import PerformanceMetrics
from backtest.yearly import (
    build_yearly_report,
    format_profit_factor,
    get_year_date_range,
    yearly_report_to_dict,
)


# ============================================================
# BACKTEST SETTINGS (SWING TRADING REVISION)
# ============================================================

# The Professor's target: Start small, protect capital, grow steadily.
INITIAL_CAPITAL = 200.0

SYSTEM_VERSION = "V2.0-Swing"

# We override the years to test the 2022 Bear Market, 2023 Sideways/Recovery, and 2024/2025 Bull Market.
TEST_YEARS = [2022, 2023, 2024, 2025]


# ============================================================
# REPORT
# ============================================================

def print_backtest_report(results):

    print()

    print("=" * 60)

    print(
        f"BACKTEST RESULTS - {SYSTEM_VERSION} "
        "COMBINED ALPHA ENGINE"
    )

    print("=" * 60)

    print(
        f"Initial Capital   : "
        f"${results['initial_capital']:.2f}"
    )

    print(
        f"Ending Capital    : "
        f"${results['ending_capital']:.2f}"
    )

    print(
        f"Total Return      : "
        f"{results['total_return_pct']:.2f}%"
    )

    print("-" * 60)

    print(
        f"Total Trades      : "
        f"{results['total_trades']}"
    )

    print(
        f"Winning Trades    : "
        f"{results['winning_trades']}"
    )

    print(
        f"Losing Trades     : "
        f"{results['losing_trades']}"
    )

    print(
        f"Win Rate          : "
        f"{results['win_rate_pct']:.2f}%"
    )

    profit_factor = (
        results["profit_factor"]
    )

    if profit_factor == float("inf"):

        print(
            "Profit Factor     : Infinity"
        )

    else:

        print(
            f"Profit Factor     : "
            f"{profit_factor:.2f}"
        )

    print(
        f"Gross Profit      : "
        f"${results['gross_profit']:.4f}"
    )

    print(
        f"Gross Loss        : "
        f"${results['gross_loss']:.4f}"
    )

    print(
        f"Average Win       : "
        f"${results['average_win']:.4f}"
    )

    print(
        f"Average Loss      : "
        f"${results['average_loss']:.4f}"
    )

    print(
        f"Payoff Ratio      : "
        f"{results['payoff_ratio']:.4f}"
    )

    print(
        f"Expectancy        : "
        f"${results['expectancy']:.4f}"
    )

    print(
        f"Best Trade        : "
        f"${results['best_trade']:.4f}"
    )

    print(
        f"Worst Trade       : "
        f"${results['worst_trade']:.4f}"
    )

    print(
        f"Average Trade     : "
        f"${results['average_trade']:.4f}"
    )

    print("-" * 60)

    print(
        f"Max Drawdown      : "
        f"{results['max_drawdown_pct']:.2f}%"
    )

    print()

    print("[DAILY STATISTICS]")

    print(
        f"Positive Days     : "
        f"{results['positive_days']}"
    )

    print(
        f"Negative Days     : "
        f"{results['negative_days']}"
    )

    print(
        f"Flat Days         : "
        f"{results['flat_days']}"
    )

    print(
        f"Best Day          : "
        f"{results['best_day_pct']:.2f}%"
    )

    print(
        f"Worst Day         : "
        f"{results['worst_day_pct']:.2f}%"
    )

    print(
        f"Avg Daily Return  : "
        f"{results['average_daily_return_pct']:.2f}%"
    )

    print()

    print("[STREAKS]")

    print(
        f"Max Win Streak    : "
        f"{results['max_winning_streak']}"
    )

    print(
        f"Max Loss Streak   : "
        f"{results['max_losing_streak']}"
    )

    print()

    print("[EXIT ANALYTICS]")

    print(
        f"STOP Exits        : "
        f"{results['stop_exits']}"
    )

    print(
        f"TARGET Exits      : "
        f"{results['target_exits']}"
    )

    print(
        f"DAILY TP2 Exits   : "
        f"{results['daily_tp2_exits']}"
    )

    print(
        f"End Backtest      : "
        f"{results['end_of_backtest_exits']}"
    )

    print(
        f"Ambiguous Exits   : "
        f"{results['ambiguous_exits']}"
    )

    print()

    print("[BACKTEST DIAGNOSTICS]")

    print(
        f"Trade Attempts    : "
        f"{results.get('trade_attempts', 0)}"
    )

    print(
        f"Ambiguous Bars    : "
        f"{results.get('ambiguous_bars', 0)}"
    )

    print(
        f"Stop Hits         : "
        f"{results.get('stop_hits', 0)}"
    )

    print(
        f"Target Hits       : "
        f"{results.get('target_hits', 0)}"
    )

    print(
        f"Daily TP1 Days    : "
        f"{results.get('daily_tp1_days', 0)}"
    )

    print(
        f"Daily TP2 Days    : "
        f"{results.get('daily_tp2_days', 0)}"
    )

    print(
        f"Daily Loss Days   : "
        f"{results.get('daily_loss_limit_days', 0)}"
    )

    print(
        f"Fundamental Contexts : "
        f"{results.get('fundamental_contexts', 0)}"
    )

    print(
        f"Fundamental Unavailable : "
        f"{results.get('fundamental_unavailable', 0)}"
    )

    print(
        f"Fundamental Rejected : "
        f"{results.get('fundamental_rejected', 0)}"
    )

    print(
        f"Multi-Factor Trades : "
        f"{results.get('multi_factor_trades', 0)}"
    )

    print(
        f"Technical Fallbacks : "
        f"{results.get('technical_fallback_trades', 0)}"
    )

    print(
        f"Final Open Risk   : "
        f"${results.get('final_open_risk', 0.0):.4f}"
    )

    print("=" * 60)


# ============================================================
# CSV METADATA VALIDATION
# ============================================================

def validate_trade_csv(
    csv_df: pd.DataFrame,
):

    print()

    print(
        f"[{SYSTEM_VERSION} TRADE METADATA VALIDATION]"
    )

    print("-" * 60)

    total_rows = len(csv_df)

    if total_rows == 0:

        print(
            "CSV boş."
        )

        return

    required_columns = [

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

    ]

    for column in required_columns:

        if column not in csv_df.columns:

            print(
                f"{column:<32}: COLUMN MISSING"
            )

            continue

        series = csv_df[column]

        available = (
            series.notna()
        ).sum()

        print(
            f"{column:<32}: "
            f"{available}/{total_rows}"
        )

    # --------------------------------------------------------
    # REGIME DISTRIBUTION
    # --------------------------------------------------------

    if "market_regime" in csv_df.columns:

        print()

        print(
            "Market Regime Distribution:"
        )

        regime_counts = (
            csv_df["market_regime"]
            .fillna("MISSING")
            .value_counts()
        )

        for regime, count in (
            regime_counts.items()
        ):

            print(
                f"  {str(regime):<22} "
                f"{count}"
            )

    # --------------------------------------------------------
    # ALPHA MODE DISTRIBUTION
    # --------------------------------------------------------

    if "alpha_mode" in csv_df.columns:

        print()

        print(
            "Alpha Mode Distribution:"
        )

        mode_counts = (
            csv_df["alpha_mode"]
            .fillna("MISSING")
            .value_counts()
        )

        for mode, count in (
            mode_counts.items()
        ):

            print(
                f"  {str(mode):<22} "
                f"{count}"
            )

    # --------------------------------------------------------
    # REGIME ADJUSTMENT DISTRIBUTION
    # --------------------------------------------------------

    if "alpha_regime_adjustment" in (
        csv_df.columns
    ):

        print()

        print(
            "Regime Adjustment Distribution:"
        )

        adjustment_counts = (
            csv_df[
                "alpha_regime_adjustment"
            ]
            .fillna("MISSING")
            .value_counts()
            .sort_index()
        )

        for adjustment, count in (
            adjustment_counts.items()
        ):

            print(
                f"  {str(adjustment):<22} "
                f"{count}"
            )

    # --------------------------------------------------------
    # ALPHA CONSISTENCY CHECK
    # --------------------------------------------------------

    required_alpha_columns = {

        "technical_score",

        "fundamental_score",

        "alpha_base_score",

        "alpha_regime_adjustment",

        "alpha_score",

    }

    if required_alpha_columns.issubset(
        csv_df.columns
    ):

        multi_factor_mask = (
            csv_df[
                "fundamental_score"
            ].notna()
        )

        if multi_factor_mask.any():

            expected_base = (
                csv_df.loc[
                    multi_factor_mask,
                    "technical_score"
                ] * 0.65
                +
                csv_df.loc[
                    multi_factor_mask,
                    "fundamental_score"
                ] * 0.35
            )

            expected_final = (
                expected_base
                +
                csv_df.loc[
                    multi_factor_mask,
                    "alpha_regime_adjustment"
                ]
            )

            actual_base = (
                csv_df.loc[
                    multi_factor_mask,
                    "alpha_base_score"
                ]
            )

            actual_final = (
                csv_df.loc[
                    multi_factor_mask,
                    "alpha_score"
                ]
            )

            base_error = (
                expected_base
                - actual_base
            ).abs().max()

            final_error = (
                expected_final
                - actual_final
            ).abs().max()

            print()

            print(
                "Alpha Formula Validation:"
            )

            print(
                f"  Max Base Error  : "
                f"{base_error:.10f}"
            )

            print(
                f"  Max Final Error : "
                f"{final_error:.10f}"
            )

    print("-" * 60)


# ============================================================
# YEARLY REPORT
# ============================================================

def print_yearly_report(report):

    print()

    print("=" * 60)

    print(
        f"YEARLY BACKTEST {report.year} "
        f"{SYSTEM_VERSION}"
    )

    print("=" * 60)

    print(
        f"Period            : "
        f"{report.start_date} -> {report.end_date}"
    )

    print(
        f"Market Bars       : "
        f"{report.bars}"
    )

    if report.error:

        print()

        print(
            f"Status            : "
            f"SKIPPED / ERROR"
        )

        print(
            f"Reason            : "
            f"{report.error}"
        )

        print("=" * 60)

        return

    print(
        f"Initial Capital   : "
        f"${report.initial_capital:.2f}"
    )

    print(
        f"Ending Capital    : "
        f"${report.ending_capital:.2f}"
    )

    print()

    print(
        f"Net Profit        : "
        f"${report.net_profit:.2f}"
    )

    print(
        f"Win rate          : "
        f"{report.win_rate_pct:.2f}%"
    )

    print(
        f"Profit factor     : "
        f"{format_profit_factor(report.profit_factor)}"
    )

    print(
        f"Max Drawdown      : "
        f"{report.max_drawdown_pct:.2f}%"
    )

    print(
        f"Number of trades  : "
        f"{report.total_trades}"
    )

    print(
        f"Annual Return     : "
        f"{report.annual_return_pct:.2f}%"
    )

    print("=" * 60)


def print_multi_year_summary(reports):

    print()

    print("=" * 60)

    print(
        f"MULTI-YEAR SUMMARY {SYSTEM_VERSION} "
        f"({TEST_YEARS[0]}-{TEST_YEARS[-1]})"
    )

    print("=" * 60)

    header = (
        f"{'Year':<6} "
        f"{'Net Profit':>14} "
        f"{'Win Rate':>10} "
        f"{'PF':>10} "
        f"{'Max DD':>10} "
        f"{'Trades':>8} "
        f"{'Return':>10}"
    )

    print(header)

    print("-" * 60)

    for report in reports:

        if report.error:

            print(
                f"{report.year:<6} "
                f"{'N/A':>14} "
                f"{'N/A':>10} "
                f"{'N/A':>10} "
                f"{'N/A':>10} "
                f"{'N/A':>8} "
                f"{'N/A':>10}"
            )

            continue

        print(
            f"{report.year:<6} "
            f"{report.net_profit:>13.2f}$ "
            f"{report.win_rate_pct:>9.2f}% "
            f"{format_profit_factor(report.profit_factor):>10} "
            f"{report.max_drawdown_pct:>9.2f}% "
            f"{report.total_trades:>8} "
            f"{report.annual_return_pct:>9.2f}%"
        )

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "AUTONOMOUS TRADING SYSTEM"
    )

    print(
        f"{SYSTEM_VERSION} - "
        "TECHNICAL + FUNDAMENTAL + REGIME"
    )

    print("=" * 60)

    settings = load_settings()

    # --------------------------------------------------------
    # RUNTIME PATH
    # --------------------------------------------------------

    project_root = (
        Path(__file__)
        .resolve()
        .parent
    )

    print()

    print(
        "[RUNTIME]"
    )

    print(
        f"Main File         : "
        f"{Path(__file__).resolve()}"
    )

    print(
        f"Project Root      : "
        f"{project_root}"
    )

    print(
        f"Engine Module     : "
        f"{Path(BacktestEngine.__module__.replace('.', '/')).name}"
    )

    # --------------------------------------------------------
    # CONFIG
    # --------------------------------------------------------

    print()
    print("[CONFIG]")

    print(
        f"Initial Capital   : "
        f"${INITIAL_CAPITAL:.2f}"
    )

    print(
        f"Timeframe         : "
        f"{settings.timeframe_minutes} minutes"
    )

    print(
        f"Universe          : "
        f"{settings.universe}"
    )

    print(
        f"Risk/Trade        : "
        f"{settings.max_risk_per_trade_pct * 100:.2f}%"
    )

    print(
        f"Max Total Risk    : "
        f"{settings.max_total_open_risk_pct * 100:.2f}%"
    )

    print(
        f"Daily Loss        : "
        f"{settings.max_daily_loss_pct * 100:.2f}%"
    )

    print(
        f"Daily TP1         : "
        f"{settings.daily_tp1_pct * 100:.2f}%"
    )

    print(
        f"Daily TP2         : "
        f"{settings.daily_tp2_pct * 100:.2f}%"
    )

    print(
        f"Max Positions     : "
        f"{settings.max_open_positions}"
    )

    print(
        f"ATR Stop          : "
        f"{settings.atr_stop_multiplier}x"
    )

    print(
        f"Risk/Reward       : "
        f"1:{settings.risk_reward_ratio}"
    )

    print(
        f"Max Exposure      : "
        f"{settings.max_position_pct * 100:.0f}%"
    )

    # --------------------------------------------------------
    # BACKTEST PERIOD
    # --------------------------------------------------------

    print()
    print("[BACKTEST PERIOD]")

    print(
        f"Years             : "
        f"{', '.join(str(year) for year in TEST_YEARS)}"
    )

    print(
        f"Independent runs  : "
        f"each year starts at ${INITIAL_CAPITAL:.2f}"
    )

    # --------------------------------------------------------
    # YEARLY BACKTESTS
    # --------------------------------------------------------

    market_data = MarketData(
        settings
    )

    yearly_reports = []

    for year in TEST_YEARS:

        start_date, end_date = (
            get_year_date_range(year)
        )

        print()
        print("=" * 60)

        print(
            f"[YEAR {year}] "
            f"{start_date} -> {end_date}"
        )

        print("=" * 60)

        print(
            "Geçmiş market verileri çekiliyor..."
        )

        try:

            df = market_data.get_historical_bars(
                start_date,
                end_date,
            )

        except Exception as error:

            report = build_yearly_report(
                year=year,
                results=None,
                error=f"Market data error: {error}",
            )

            yearly_reports.append(report)

            print_yearly_report(report)

            continue

        if df is None or df.empty:

            report = build_yearly_report(
                year=year,
                results=None,
                error="Aucune donnée de marché pour cette année.",
            )

            yearly_reports.append(report)

            print_yearly_report(report)

            continue

        print(
            f"Toplam satır: {len(df)}"
        )

        engine = BacktestEngine(
            settings=settings,
            config=BacktestConfig(
                initial_capital=INITIAL_CAPITAL
            ),
        )

        print(
            f"{SYSTEM_VERSION} backtest {year} "
            "çalıştırılıyor..."
        )

        try:

            results = engine.run(df)

        except Exception as error:

            report = build_yearly_report(
                year=year,
                results=None,
                bars=len(df),
                error=f"Backtest error: {error}",
            )

            yearly_reports.append(report)

            print_yearly_report(report)

            continue

        report = build_yearly_report(
            year=year,
            results=results,
            bars=len(df),
        )

        yearly_reports.append(report)

        print_yearly_report(report)

        print_backtest_report(
            results
        )

        csv_filename = (
            project_root
            / f"trade_analytics_{year}.csv"
        )

        exported_df = (
            PerformanceMetrics(
                engine.portfolio
            )
            .export_trades_to_csv(
                str(csv_filename)
            )
        )

        if exported_df is not None:

            print(
                f">>> '{csv_filename}' "
                "başarıyla oluşturuldu."
            )

            validate_trade_csv(
                exported_df
            )

        else:

            print()

            print(
                f"[{SYSTEM_VERSION}] {year}: export edilecek "
                "trade bulunamadı."
            )

    # --------------------------------------------------------
    # MULTI-YEAR SUMMARY
    # --------------------------------------------------------

    print_multi_year_summary(
        yearly_reports
    )

    summary_filename = (
        project_root
        / "yearly_backtest_summary.csv"
    )

    pd.DataFrame(
        [
            yearly_report_to_dict(report)
            for report in yearly_reports
        ]
    ).to_csv(
        summary_filename,
        index=False,
    )

    print()

    print(
        f">>> '{summary_filename}' "
        "başarıyla oluşturuldu."
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print()

    print(
        f"[{SYSTEM_VERSION}] "
        "Yearly historical backtests tamamlandı."
    )


if __name__ == "__main__":
    main()