from __future__ import annotations

import sys
from pathlib import Path

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from data.fundamental_data import FundamentalData
from data.financial_statement import FinancialStatementEngine


def main():

    symbol = "MSFT"
    as_of_date = "2025-01-15"

    fundamental_data = FundamentalData()

    engine = FinancialStatementEngine(
        fundamental_data
    )

    facts = fundamental_data.get_company_facts(
        symbol
    )

    if facts is None:

        print(
            "MSFT company facts bulunamadı."
        )

        return

    us_gaap = (
        facts
        .get("facts", {})
        .get("us-gaap", {})
    )

    print("=" * 90)
    print("MSFT RAW FUNDAMENTAL DEBUG")
    print("=" * 90)

    print()
    print(
        "TARGET ANNUAL END DATE: 2024-06-30"
    )
    print()

    # ========================================================
    # RAW SEC CHECK
    # ========================================================

    for field_name, tags in (
        engine.TAG_CANDIDATES.items()
    ):

        print("=" * 90)
        print(
            f"FIELD: {field_name}"
        )
        print("=" * 90)

        for tag in tags:

            fact = us_gaap.get(
                tag
            )

            print()
            print(
                f"TAG: {tag}"
            )

            if fact is None:

                print(
                    "  FACT YOK"
                )

                continue

            units = fact.get(
                "units",
                {}
            )

            if not units:

                print(
                    "  UNIT YOK"
                )

                continue

            for unit_name, entries in (
                units.items()
            ):

                print(
                    f"  UNIT: {unit_name}"
                )

                matches = []

                for entry in entries:

                    filed = entry.get(
                        "filed"
                    )

                    if (
                        filed is None
                        or filed[:10]
                        > as_of_date
                    ):

                        continue

                    end = entry.get(
                        "end"
                    )

                    if end is None:
                        continue

                    if (
                        end[:10]
                        != "2024-06-30"
                    ):

                        continue

                    matches.append(
                        entry
                    )

                if not matches:

                    print(
                        "    2024-06-30 KAYDI YOK"
                    )

                    continue

                matches.sort(
                    key=lambda entry: (
                        entry.get(
                            "filed",
                            ""
                        ),
                    )
                )

                for entry in matches:

                    duration = (
                        engine._duration_days(
                            entry.get(
                                "start"
                            ),
                            entry.get(
                                "end"
                            ),
                        )
                    )

                    print()
                    print(
                        "    START   :",
                        entry.get("start")
                    )

                    print(
                        "    END     :",
                        entry.get("end")
                    )

                    print(
                        "    FILED   :",
                        entry.get("filed")
                    )

                    print(
                        "    FORM    :",
                        entry.get("form")
                    )

                    print(
                        "    FY      :",
                        entry.get("fy")
                    )

                    print(
                        "    FP      :",
                        entry.get("fp")
                    )

                    print(
                        "    FRAME   :",
                        entry.get("frame")
                    )

                    print(
                        "    DURATION:",
                        duration
                    )

                    print(
                        "    VALUE   :",
                        entry.get("val")
                    )

    # ========================================================
    # ANNUAL MAP CHECK
    # ========================================================

    print()
    print("=" * 90)
    print(
        "ENGINE ANNUAL MAP CHECK"
    )
    print("=" * 90)

    (
        quarterly_maps,
        annual_maps,
    ) = engine._build_field_maps(
        facts,
        as_of_date,
    )

    for field_name in (
        engine.TAG_CANDIDATES
    ):

        annual_entries = (
            annual_maps.get(
                field_name,
                []
            )
        )

        print()
        print(
            f"[{field_name}] "
            "annual entries ending 2024-06-30:"
        )

        found = False

        for entry in annual_entries:

            end = entry.get(
                "end"
            )

            if (
                end is not None
                and end[:10]
                == "2024-06-30"
            ):

                found = True

                print(
                    entry
                )

        if not found:

            print(
                "  NONE"
            )

    # ========================================================
    # QUARTER MAP CHECK
    # ========================================================

    print()
    print("=" * 90)
    print(
        "ENGINE QUARTER MAP CHECK"
    )
    print("=" * 90)

    for field_name in (
        engine.TAG_CANDIDATES
    ):

        quarter_map = (
            quarterly_maps.get(
                field_name,
                {}
            )
        )

        print()
        print(
            f"[{field_name}]"
        )

        recent_entries = []

        for (
            key,
            entry,
        ) in quarter_map.items():

            if (
                key[1]
                >= "2023-09-01"
            ):

                recent_entries.append(
                    (
                        key,
                        entry
                    )
                )

        recent_entries.sort(
            key=lambda item: (
                item[0][1],
                item[0][0],
            )
        )

        for (
            key,
            entry,
        ) in recent_entries:

            print(
                key,
                "filed=",
                entry.get("filed"),
                "fy=",
                entry.get("fy"),
                "fp=",
                entry.get("fp"),
                "val=",
                entry.get("val"),
            )

    # ========================================================
    # FINAL ENGINE HISTORY
    # ========================================================

    print()
    print("=" * 90)
    print(
        "FINAL ENGINE HISTORY"
    )
    print("=" * 90)

    history = (
        engine.get_quarterly_history(
            symbol,
            as_of_date=as_of_date,
            limit=12,
        )
    )

    for period in history:

        print(
            period.end_date,
            "|",
            period.start_date,
            "|",
            period.fiscal_year,
            period.fiscal_period,
            "| Revenue=",
            period.revenue,
            "| NI=",
            period.net_income,
            "| EPS=",
            period.eps,
        )


if __name__ == "__main__":
    main()