from backtest.yearly import (
    BACKTEST_YEARS,
    build_yearly_report,
    format_profit_factor,
    get_year_date_range,
    yearly_report_to_dict,
)


def test_backtest_years_cover_2020_to_2025():
    assert BACKTEST_YEARS == (
        2020,
        2021,
        2022,
        2023,
        2024,
        2025,
    )


def test_year_date_range_is_full_calendar_year():
    assert get_year_date_range(2020) == (
        "2020-01-01",
        "2020-12-31",
    )

    assert get_year_date_range(2025) == (
        "2025-01-01",
        "2025-12-31",
    )


def test_build_yearly_report_maps_core_metrics():
    report = build_yearly_report(
        year=2024,
        results={
            "initial_capital": 10000.0,
            "ending_capital": 11250.0,
            "win_rate_pct": 55.5,
            "profit_factor": 1.8,
            "max_drawdown_pct": -12.4,
            "total_trades": 40,
            "total_return_pct": 12.5,
        },
        bars=1000,
    )

    assert report.year == 2024
    assert report.start_date == "2024-01-01"
    assert report.end_date == "2024-12-31"
    assert report.bars == 1000
    assert report.net_profit == 1250.0
    assert report.win_rate_pct == 55.5
    assert report.profit_factor == 1.8
    assert report.max_drawdown_pct == -12.4
    assert report.total_trades == 40
    assert report.annual_return_pct == 12.5
    assert report.error is None


def test_build_yearly_report_without_results():
    report = build_yearly_report(
        year=2021,
        results=None,
        error="Aucune donnée de marché pour cette année.",
    )

    assert report.total_trades == 0
    assert report.net_profit == 0.0
    assert report.annual_return_pct == 0.0
    assert report.error is not None


def test_yearly_report_to_dict_includes_requested_metrics():
    report = build_yearly_report(
        year=2023,
        results={
            "initial_capital": 10000.0,
            "ending_capital": 9000.0,
            "win_rate_pct": 40.0,
            "profit_factor": 0.7,
            "max_drawdown_pct": -18.0,
            "total_trades": 12,
            "total_return_pct": -10.0,
        },
    )

    payload = yearly_report_to_dict(report)

    assert payload["net_profit"] == -1000.0
    assert payload["win_rate_pct"] == 40.0
    assert payload["profit_factor"] == 0.7
    assert payload["max_drawdown_pct"] == -18.0
    assert payload["total_trades"] == 12
    assert payload["annual_return_pct"] == -10.0


def test_format_profit_factor_infinity():
    assert format_profit_factor(float("inf")) == "Infinity"
    assert format_profit_factor(1.234) == "1.23"
