from __future__ import annotations
from data.fundamental_data import FundamentalData
from data.financial_statement import FinancialStatementEngine

# ============================================================
# CONFIG
# ============================================================
SYMBOLS = [
    "AAPL",
    "META",
    "NVDA",
    "MSFT",
]
AS_OF_DATE = "2025-01-15"
LIMIT = 12

# ============================================================
# DISPLAY
# ============================================================
def print_separator():
    print("=" * 100)

def print_period(
    index: int,
    period,
):
    print(
        f"{index:>3} | "
        f"{period.end_date:<12} | "
        f"{period.start_date:<12} | "
        f"{period.filed_date:<12} | "
        f"{str(period.fiscal_year):<6} | "
        f"{str(period.fiscal_period):<4} | "
        f"Revenue={str(period.revenue):<14} | "
        f"NetIncome={str(period.net_income):<14} | "
        f"EPS={str(period.eps):<14}"
    )

# ============================================================
# REAL DATA DIAGNOSTIC
# ============================================================
def inspect_symbol(
    engine: FinancialStatementEngine,
    symbol: str,
):
    print()
    print_separator()

    print(
        f"REAL FUNDAMENTAL HISTORY: "
        f"{symbol}"
    )

    print(
        f"As Of Date: {AS_OF_DATE}"
    )

    print_separator()

    periods = engine.get_quarterly_history(
        symbol=symbol,
        as_of_date=AS_OF_DATE,
        limit=LIMIT,
    )

    print(
        "IDX | END DATE     | START DATE   | FILED DATE   | FY     | FP   | "
        "Revenue        | NetIncome      | EPS"
    )

    print("-" * 100)

    if not periods:

        print(
            "No quarterly periods returned."
        )

        return

    for index, period in enumerate(
        periods,
        start=1,
    ):

        print_period(
            index,
            period,
        )

    print()

    # ========================================================
    # CHRONOLOGICAL CHECK
    # ========================================================

    end_dates = [
        period.end_date
        for period in periods
    ]

    chronological = (
        end_dates
        == sorted(end_dates)
    )

    print(
        f"Chronological Order : "
        f"{chronological}"
    )

    # ========================================================
    # LAST / PREVIOUS / YEAR AGO
    # ========================================================

    if len(periods) >= 2:

        latest = periods[-1]
        previous = periods[-2]

        print()

        print(
            "[QOQ CHECK]"
        )

        print(
            f"Latest Quarter     : "
            f"{latest.end_date} | "
            f"FY={latest.fiscal_year} "
            f"FP={latest.fiscal_period}"
        )

        print(
            f"Previous Quarter   : "
            f"{previous.end_date} | "
            f"FY={previous.fiscal_year} "
            f"FP={previous.fiscal_period}"
        )

        if (
            latest.revenue is not None
            and previous.revenue is not None
            and previous.revenue != 0
        ):

            revenue_qoq = (
                latest.revenue
                / previous.revenue
            ) - 1.0

            print(
                f"Revenue QoQ        : "
                f"{revenue_qoq:.6%}"
            )

        if (
            latest.net_income is not None
            and previous.net_income is not None
            and previous.net_income != 0
        ):

            net_income_qoq = (
                latest.net_income
                / previous.net_income
            ) - 1.0

            print(
                f"Net Income QoQ     : "
                f"{net_income_qoq:.6%}"
            )

        if (
            latest.eps is not None
            and previous.eps is not None
            and previous.eps != 0
        ):

            eps_qoq = (
                latest.eps
                / previous.eps
            ) - 1.0

            print(
                f"EPS QoQ            : "
                f"{eps_qoq:.6%}"
            )

    # ========================================================
    # YOY CHECK
    # ========================================================

    if len(periods) >= 5:

        latest = periods[-1]
        year_ago = periods[-5]

        print()

        print(
            "[YOY CHECK]"
        )

        print(
            f"Latest Quarter     : "
            f"{latest.end_date} | "
            f"FY={latest.fiscal_year} "
            f"FP={latest.fiscal_period}"
        )

        print(
            f"Year Ago Quarter   : "
            f"{year_ago.end_date} | "
            f"FY={year_ago.fiscal_year} "
            f"FP={year_ago.fiscal_period}"
        )

        if (
            latest.revenue is not None
            and year_ago.revenue is not None
            and year_ago.revenue != 0
        ):

            revenue_yoy = (
                latest.revenue
                / year_ago.revenue
            ) - 1.0

            print(
                f"Revenue YoY        : "
                f"{revenue_yoy:.6%}"
            )

        if (
            latest.net_income is not None
            and year_ago.net_income is not None
            and year_ago.net_income != 0
        ):

            net_income_yoy = (
                latest.net_income
                / year_ago.net_income
            ) - 1.0

            print(
                f"Net Income YoY     : "
                f"{net_income_yoy:.6%}"
            )

        if (
            latest.eps is not None
            and year_ago.eps is not None
            and year_ago.eps != 0
        ):

            eps_yoy = (
                latest.eps
                / year_ago.eps
            ) - 1.0

            print(
                f"EPS YoY            : "
                f"{eps_yoy:.6%}"
            )

    # ========================================================
    # TTM CHECK
    # ========================================================

    ttm = engine.get_ttm(
        symbol=symbol,
        as_of_date=AS_OF_DATE,
    )

    print()

    print(
        "[ENGINE TTM CHECK]"
    )

    if ttm is None:

        print(
            "TTM unavailable."
        )

        return

    print(
        f"Latest Quarter End : "
        f"{ttm.latest_quarter_end}"
    )

    print(
        f"Revenue TTM        : "
        f"{ttm.revenue_ttm}"
    )

    print(
        f"Net Income TTM     : "
        f"{ttm.net_income_ttm}"
    )

    print(
        f"EPS TTM            : "
        f"{ttm.eps_ttm}"
    )

    print(
        f"Revenue QoQ        : "
        f"{ttm.revenue_qoq}"
    )

    print(
        f"Revenue YoY        : "
        f"{ttm.revenue_yoy}"
    )

    print(
        f"Net Income QoQ     : "
        f"{ttm.net_income_qoq}"
    )

    print(
        f"Net Income YoY     : "
        f"{ttm.net_income_yoy}"
    )

    print(
        f"EPS QoQ            : "
        f"{ttm.eps_qoq}"
    )

    print(
        f"EPS YoY            : "
        f"{ttm.eps_yoy}"
    )

# ============================================================
# PYTEST
# ============================================================
def test_real_fundamental_history():

    fundamental_data = FundamentalData(
        settings=None
    )

    engine = FinancialStatementEngine(
        fundamental_data
    )

    for symbol in SYMBOLS:

        periods = engine.get_quarterly_history(
            symbol=symbol,
            as_of_date=AS_OF_DATE,
            limit=LIMIT,
        )

        print()
        print_separator()
        print(
            f"DIAGNOSTIC TEST: {symbol}"
        )
        print_separator()

        print(
            f"Periods returned: "
            f"{len(periods)}"
        )

        assert periods, (
            f"No quarterly history for {symbol}"
        )

        end_dates = [
            period.end_date
            for period in periods
        ]

        assert end_dates == sorted(
            end_dates
        ), (
            f"{symbol}: periods are not chronological"
        )

        if len(periods) >= 2:

            latest = periods[-1]
            previous = periods[-2]

            assert latest.end_date >= previous.end_date

        inspect_symbol(
            engine,
            symbol,
        )