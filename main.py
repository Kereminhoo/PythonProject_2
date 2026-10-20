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
# BACKTEST SETTINGS (V3.1 COMPOUNDING & WARM-UP EDITION)
# ============================================================

INITIAL_CAPITAL = 200.0
SYSTEM_VERSION = "V3.1-Swing-Compound"
TEST_YEARS = [2022, 2023, 2024, 2025]

# True olduğunda her yılın bitiş kasası bir sonraki yılın başlangıç kasası olur!
COMPOUND_ACROSS_YEARS = True

# Ocak-Mart rallilerini kaçırmamak için indikatör ısıtma süresi (Takvim günü)
WARMUP_CALENDAR_DAYS = 130


# ============================================================
# REPORT
# ============================================================

def print_backtest_report(results):
    print()
    print("=" * 60)
    print(f"BACKTEST RESULTS - {SYSTEM_VERSION} COMBINED ALPHA ENGINE")
    print("=" * 60)
    print(f"Initial Capital   : ${results['initial_capital']:.2f}")
    print(f"Ending Capital    : ${results['ending_capital']:.2f}")
    print(f"Total Return      : {results['total_return_pct']:.2f}%")
    print("-" * 60)
    print(f"Total Trades      : {results['total_trades']}")
    print(f"Winning Trades    : {results['winning_trades']}")
    print(f"Losing Trades     : {results['losing_trades']}")
    print(f"Win Rate          : {results['win_rate_pct']:.2f}%")

    profit_factor = results["profit_factor"]
    if profit_factor == float("inf"):
        print("Profit Factor     : Infinity")
    else:
        print(f"Profit Factor     : {profit_factor:.2f}")

    print(f"Gross Profit      : ${results['gross_profit']:.4f}")
    print(f"Gross Loss        : ${results['gross_loss']:.4f}")
    print(f"Average Win       : ${results['average_win']:.4f}")
    print(f"Average Loss      : ${results['average_loss']:.4f}")
    print(f"Payoff Ratio      : {results['payoff_ratio']:.4f}")
    print(f"Expectancy        : ${results['expectancy']:.4f}")
    print(f"Best Trade        : ${results['best_trade']:.4f}")
    print(f"Worst Trade       : ${results['worst_trade']:.4f}")
    print(f"Average Trade     : ${results['average_trade']:.4f}")
    print("-" * 60)
    print(f"Max Drawdown      : {results['max_drawdown_pct']:.2f}%")
    print()
    print("[DAILY STATISTICS]")
    print(f"Positive Days     : {results['positive_days']}")
    print(f"Negative Days     : {results['negative_days']}")
    print(f"Flat Days         : {results['flat_days']}")
    print(f"Best Day          : {results['best_day_pct']:.2f}%")
    print(f"Worst Day         : {results['worst_day_pct']:.2f}%")
    print(f"Avg Daily Return  : {results['average_daily_return_pct']:.2f}%")
    print()
    print("[STREAKS]")
    print(f"Max Win Streak    : {results['max_winning_streak']}")
    print(f"Max Loss Streak   : {results['max_losing_streak']}")
    print()
    print("[EXIT ANALYTICS]")
    print(f"STOP Exits        : {results['stop_exits']}")
    print(f"TARGET Exits      : {results['target_exits']}")
    print(f"DAILY TP2 Exits   : {results['daily_tp2_exits']}")
    print(f"End Backtest      : {results['end_of_backtest_exits']}")
    print(f"Ambiguous Exits   : {results['ambiguous_exits']}")
    print()
    print("[BACKTEST DIAGNOSTICS]")
    print(f"Trade Attempts    : {results.get('trade_attempts', 0)}")
    print(f"Ambiguous Bars    : {results.get('ambiguous_bars', 0)}")
    print(f"Stop Hits         : {results.get('stop_hits', 0)}")
    print(f"Target Hits       : {results.get('target_hits', 0)}")
    print(f"Daily TP1 Days    : {results.get('daily_tp1_days', 0)}")
    print(f"Daily TP2 Days    : {results.get('daily_tp2_days', 0)}")
    print(f"Daily Loss Days   : {results.get('daily_loss_limit_days', 0)}")
    print(f"Fundamental Contexts : {results.get('fundamental_contexts', 0)}")
    print(f"Fundamental Unavailable : {results.get('fundamental_unavailable', 0)}")
    print(f"Fundamental Rejected : {results.get('fundamental_rejected', 0)}")
    print(f"Multi-Factor Trades : {results.get('multi_factor_trades', 0)}")
    print(f"Technical Fallbacks : {results.get('technical_fallback_trades', 0)}")
    print(f"Final Open Risk   : ${results.get('final_open_risk', 0.0):.4f}")
    print("=" * 60)


# ============================================================
# CSV METADATA VALIDATION
# ============================================================

def validate_trade_csv(csv_df: pd.DataFrame):
    print()
    print(f"[{SYSTEM_VERSION} TRADE METADATA VALIDATION]")
    print("-" * 60)

    total_rows = len(csv_df)
    if total_rows == 0:
        print("CSV boş.")
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
            print(f"{column:<32}: COLUMN MISSING")
            continue
        series = csv_df[column]
        available = series.notna().sum()
        print(f"{column:<32}: {available}/{total_rows}")

    if "market_regime" in csv_df.columns:
        print("\nMarket Regime Distribution:")
        regime_counts = csv_df["market_regime"].fillna("MISSING").value_counts()
        for regime, count in regime_counts.items():
            print(f"  {str(regime):<22} {count}")

    if "alpha_mode" in csv_df.columns:
        print("\nAlpha Mode Distribution:")
        mode_counts = csv_df["alpha_mode"].fillna("MISSING").value_counts()
        for mode, count in mode_counts.items():
            print(f"  {str(mode):<22} {count}")

    print("-" * 60)


# ============================================================
# YEARLY REPORT
# ============================================================

def print_yearly_report(report):
    print()
    print("=" * 60)
    print(f"YEARLY BACKTEST {report.year} {SYSTEM_VERSION}")
    print("=" * 60)
    print(f"Period            : {report.start_date} -> {report.end_date}")
    print(f"Market Bars       : {report.bars}")

    if report.error:
        print()
        print("Status            : SKIPPED / ERROR")
        print(f"Reason            : {report.error}")
        print("=" * 60)
        return

    print(f"Initial Capital   : ${report.initial_capital:.2f}")
    print(f"Ending Capital    : ${report.ending_capital:.2f}")
    print()
    print(f"Net Profit        : ${report.net_profit:.2f}")
    print(f"Win rate          : {report.win_rate_pct:.2f}%")
    print(f"Profit factor     : {format_profit_factor(report.profit_factor)}")
    print(f"Max Drawdown      : {report.max_drawdown_pct:.2f}%")
    print(f"Number of trades  : {report.total_trades}")
    print(f"Annual Return     : {report.annual_return_pct:.2f}%")
    print("=" * 60)


def print_multi_year_summary(reports, initial_cap: float, final_cap: float):
    print()
    print("=" * 76)
    print(
        f"MULTI-YEAR SUMMARY {SYSTEM_VERSION} "
        f"({TEST_YEARS[0]}-{TEST_YEARS[-1]}) "
        f"[COMPOUNDING: {'ON' if COMPOUND_ACROSS_YEARS else 'OFF'}]"
    )
    print("=" * 76)

    header = (
        f"{'Year':<6} "
        f"{'Start Cap':>11} "
        f"{'End Cap':>11} "
        f"{'Net Profit':>12} "
        f"{'Win Rate':>9} "
        f"{'PF':>7} "
        f"{'Max DD':>8} "
        f"{'Trades':>7} "
        f"{'Return':>9}"
    )
    print(header)
    print("-" * 76)

    for report in reports:
        if report.error:
            print(f"{report.year:<6} {'ERROR / SKIPPED':>68}")
            continue

        print(
            f"{report.year:<6} "
            f"${report.initial_capital:>10.2f} "
            f"${report.ending_capital:>10.2f} "
            f"${report.net_profit:>11.2f} "
            f"{report.win_rate_pct:>8.2f}% "
            f"{format_profit_factor(report.profit_factor):>7} "
            f"{report.max_drawdown_pct:>7.2f}% "
            f"{report.total_trades:>7} "
            f"{report.annual_return_pct:>8.2f}%"
        )

    print("=" * 76)
    total_net_profit = final_cap - initial_cap
    total_compound_return_pct = ((final_cap / initial_cap) - 1.0) * 100.0 if initial_cap > 0 else 0.0
    print(f"STARTING CAPITAL (2022) : ${initial_cap:.2f}")
    print(f"FINAL CAPITAL    (2025) : ${final_cap:.2f}")
    print(f"TOTAL NET PROFIT        : ${total_net_profit:.2f}")
    print(f"TOTAL COMPOUND RETURN   : {total_compound_return_pct:.2f}%")
    print("=" * 76)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("AUTONOMOUS TRADING SYSTEM")
    print(f"{SYSTEM_VERSION} - TECHNICAL + FUNDAMENTAL + REGIME")
    print("=" * 60)

    settings = load_settings()
    project_root = Path(__file__).resolve().parent

    print("\n[RUNTIME]")
    print(f"Main File         : {Path(__file__).resolve()}")
    print(f"Project Root      : {project_root}")
    print(f"Engine Module     : {Path(BacktestEngine.__module__.replace('.', '/')).name}")

    print("\n[CONFIG]")
    print(f"Initial Capital   : ${INITIAL_CAPITAL:.2f}")
    print(f"Timeframe         : {settings.timeframe_minutes} minutes")
    print(f"Universe          : {settings.universe}")
    print(f"Non-Tradable      : {getattr(settings, 'non_tradable_symbols', ('SPY',))}")
    print(f"Base Risk/Trade   : {settings.max_risk_per_trade_pct * 100:.2f}%")
    if getattr(settings, "use_dynamic_risk", False):
        print(f"High-Alpha Risk   : {getattr(settings, 'high_alpha_risk_pct', 0)*100:.2f}% (Alpha >= {getattr(settings, 'high_alpha_threshold', 80)})")
    print(f"Max Total Risk    : {settings.max_total_open_risk_pct * 100:.2f}%")
    print(f"Daily Loss        : {settings.max_daily_loss_pct * 100:.2f}%")
    print(f"Max Positions     : {settings.max_open_positions} (Active Risk)")
    print(f"ATR Stop          : {settings.atr_stop_multiplier}x")
    print(f"Max Exposure      : {settings.max_position_pct * 100:.0f}% (2x Reg-T Buying Power)")

    print("\n[BACKTEST PERIOD]")
    print(f"Years             : {', '.join(str(year) for year in TEST_YEARS)}")
    print(f"Compounding Mode  : {'ENABLED (Snowball Effect)' if COMPOUND_ACROSS_YEARS else 'DISABLED (Reset to $200)'}")
    print(f"Indicator Warm-Up : {WARMUP_CALENDAR_DAYS} calendar days prior to Jan 1")

    market_data = MarketData(settings)
    yearly_reports = []
    
    running_capital = INITIAL_CAPITAL

    for year in TEST_YEARS:
        start_date, end_date = get_year_date_range(year)
        
        # İndikatörlerin (EMA 50, Ichimoku 52) 2 Ocak sabahı hazır olması için
        # veriyi 130 takvim günü (~90 işlem günü) öncesinden çekiyoruz!
        warmup_start_date = (
            pd.Timestamp(start_date) - pd.Timedelta(days=WARMUP_CALENDAR_DAYS)
        ).strftime("%Y-%m-%d")

        year_start_capital = running_capital if COMPOUND_ACROSS_YEARS else INITIAL_CAPITAL

        print()
        print("=" * 60)
        print(f"[YEAR {year}] {start_date} -> {end_date} (Warm-up from {warmup_start_date})")
        print(f"Starting Capital  : ${year_start_capital:.2f}")
        print("=" * 60)
        print("Geçmiş market verileri çekiliyor...")

        try:
            df = market_data.get_historical_bars(
                warmup_start_date,
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

        print(f"Toplam satır (Warm-up dahil): {len(df)}")

        engine = BacktestEngine(
            settings=settings,
            config=BacktestConfig(
                initial_capital=year_start_capital
            ),
        )

        print(f"{SYSTEM_VERSION} backtest {year} çalıştırılıyor...")

        try:
            # İndikatörler tüm df (warm-up dahil) üzerinde hesaplanır,
            # ancak işlemler tam start_date (1 Ocak) tarihinde başlar!
            results = engine.run(
                df,
                start_date=start_date,
                end_date=end_date,
            )
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

        # Bileşik kasa güncellemesi
        if COMPOUND_ACROSS_YEARS and "ending_capital" in results:
            running_capital = float(results["ending_capital"])

        report = build_yearly_report(
            year=year,
            results=results,
            bars=len(df),
        )

        yearly_reports.append(report)
        print_yearly_report(report)
        print_backtest_report(results)

        csv_filename = project_root / f"trade_analytics_{year}.csv"
        exported_df = PerformanceMetrics(engine.portfolio).export_trades_to_csv(
            str(csv_filename)
        )

        if exported_df is not None:
            print(f">>> '{csv_filename}' başarıyla oluşturuldu.")
            validate_trade_csv(exported_df)
        else:
            print(f"\n[{SYSTEM_VERSION}] {year}: export edilecek trade bulunamadı.")

    # MULTI-YEAR SUMMARY
    print_multi_year_summary(
        yearly_reports,
        initial_cap=INITIAL_CAPITAL,
        final_cap=running_capital,
    )

    summary_filename = project_root / "yearly_backtest_summary.csv"
    pd.DataFrame(
        [yearly_report_to_dict(report) for report in yearly_reports]
    ).to_csv(summary_filename, index=False)

    print(f"\n>>> '{summary_filename}' başarıyla oluşturuldu.")
    print(f"\n[{SYSTEM_VERSION}] Yearly historical backtests tamamlandı.")


if __name__ == "__main__":
    main()