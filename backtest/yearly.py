from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


BACKTEST_YEARS = (
    2020,
    2021,
    2022,
    2023,
    2024,
    2025,
)


@dataclass(frozen=True)
class YearlyReport:
    year: int
    start_date: str
    end_date: str
    bars: int
    initial_capital: float
    ending_capital: float
    net_profit: float
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    total_trades: int
    annual_return_pct: float
    error: str | None = None


def get_year_date_range(year: int) -> tuple[str, str]:
    return (
        f"{year}-01-01",
        f"{year}-12-31",
    )


def format_profit_factor(value: float) -> str:
    if value == float("inf"):
        return "Infinity"

    return f"{value:.2f}"


def build_yearly_report(
    year: int,
    results: dict | None,
    bars: int = 0,
    error: str | None = None,
) -> YearlyReport:
    start_date, end_date = get_year_date_range(year)

    if results is None:
        return YearlyReport(
            year=year,
            start_date=start_date,
            end_date=end_date,
            bars=bars,
            initial_capital=0.0,
            ending_capital=0.0,
            net_profit=0.0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            max_drawdown_pct=0.0,
            total_trades=0,
            annual_return_pct=0.0,
            error=error,
        )

    initial_capital = float(
        results.get("initial_capital", 0.0)
    )
    ending_capital = float(
        results.get("ending_capital", 0.0)
    )

    return YearlyReport(
        year=year,
        start_date=start_date,
        end_date=end_date,
        bars=bars,
        initial_capital=initial_capital,
        ending_capital=ending_capital,
        net_profit=ending_capital - initial_capital,
        win_rate_pct=float(
            results.get("win_rate_pct", 0.0)
        ),
        profit_factor=float(
            results.get("profit_factor", 0.0)
        ),
        max_drawdown_pct=float(
            results.get("max_drawdown_pct", 0.0)
        ),
        total_trades=int(
            results.get("total_trades", 0)
        ),
        annual_return_pct=float(
            results.get("total_return_pct", 0.0)
        ),
        error=error,
    )


def yearly_report_to_dict(report: YearlyReport) -> dict:
    return {
        "year": report.year,
        "start_date": report.start_date,
        "end_date": report.end_date,
        "bars": report.bars,
        "initial_capital": report.initial_capital,
        "ending_capital": report.ending_capital,
        "net_profit": report.net_profit,
        "win_rate_pct": report.win_rate_pct,
        "profit_factor": report.profit_factor,
        "max_drawdown_pct": report.max_drawdown_pct,
        "total_trades": report.total_trades,
        "annual_return_pct": report.annual_return_pct,
        "error": report.error or "",
    }


def iter_backtest_years(
    years: Iterable[int] | None = None,
) -> tuple[int, ...]:
    if years is None:
        return BACKTEST_YEARS

    return tuple(years)
