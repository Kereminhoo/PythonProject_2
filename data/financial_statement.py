from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from data.fundamental_data import FundamentalData


# ============================================================
# FINANCIAL PERIOD
# ============================================================

@dataclass
class FinancialPeriod:

    symbol: str

    start_date: str
    end_date: str
    filed_date: str

    form: Optional[str]
    fiscal_year: Optional[int]
    fiscal_period: Optional[str]

    revenue: Optional[float]
    net_income: Optional[float]
    eps: Optional[float]

    operating_cash_flow: Optional[float]
    capital_expenditure: Optional[float]

    free_cash_flow: Optional[float]

    # Point-in-time filing identity
    filing_accession: Optional[str] = None
    filing_acceptance_datetime: Optional[str] = None


# ============================================================
# TTM FINANCIALS
# ============================================================

@dataclass
class TTMFinancials:

    symbol: str

    as_of_date: Optional[str]

    latest_quarter_end: Optional[str]

    revenue_ttm: Optional[float]
    net_income_ttm: Optional[float]
    eps_ttm: Optional[float]

    operating_cash_flow_ttm: Optional[float]
    capital_expenditure_ttm: Optional[float]
    free_cash_flow_ttm: Optional[float]

    revenue_qoq: Optional[float]
    revenue_yoy: Optional[float]

    net_income_qoq: Optional[float]
    net_income_yoy: Optional[float]

    eps_qoq: Optional[float]
    eps_yoy: Optional[float]

    fcf_yoy: Optional[float]

    # Point-in-time filing identity
    latest_filing_accession: Optional[str] = None
    latest_filing_acceptance_datetime: Optional[str] = None


# ============================================================
# FINANCIAL STATEMENT ENGINE
# ============================================================

class FinancialStatementEngine:

    TAG_CANDIDATES = {

        "revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],

        "net_income": [
            "NetIncomeLoss",
            "ProfitLoss",
        ],

        "eps": [
            "EarningsPerShareDiluted",
            "EarningsPerShareBasic",
        ],

        "operating_cash_flow": [
            "NetCashProvidedByUsedInOperatingActivities",
        ],

        "capital_expenditure": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
        ],
    }

    # ========================================================
    # DURATION CONSTANTS
    # ========================================================

    QUARTER_MIN_DAYS = 70
    QUARTER_MAX_DAYS = 120

    ANNUAL_MIN_DAYS = 300
    ANNUAL_MAX_DAYS = 380

    QUARTER_GAP_TOLERANCE_DAYS = 20

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        fundamental_data: FundamentalData,
    ):
        self.fundamental_data = fundamental_data

    # ========================================================
    # DATE
    # ========================================================

    @staticmethod
    def _normalize_date(
        value: Optional[str | date | datetime],
    ) -> Optional[str]:

        if value is None:
            return None

        if isinstance(
            value,
            datetime,
        ):
            return value.date().isoformat()

        if isinstance(
            value,
            date,
        ):
            return value.isoformat()

        return str(value)[:10]

    # ========================================================
    # POINT-IN-TIME NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_as_of(
        value: Optional[str | date | datetime],
    ) -> tuple[
        Optional[str],
        Optional[datetime],
    ]:

        return FundamentalData._normalize_as_of(
            value
        )

    # ========================================================
    # PARSE DATE
    # ========================================================

    @staticmethod
    def _parse_date(
        value: Optional[str],
    ) -> Optional[date]:

        if value is None:
            return None

        try:

            return date.fromisoformat(
                value[:10]
            )

        except ValueError:

            return None

    # ========================================================
    # DURATION
    # ========================================================

    @classmethod
    def _duration_days(
        cls,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Optional[int]:

        start = cls._parse_date(
            start_date
        )

        end = cls._parse_date(
            end_date
        )

        if (
            start is None
            or end is None
        ):

            return None

        return (
            end - start
        ).days + 1

    # ========================================================
    # FIND FACT
    # ========================================================

    @classmethod
    def _find_fact(
        cls,
        facts: dict,
        field_name: str,
    ) -> Optional[dict]:

        us_gaap = (
            facts
            .get(
                "facts",
                {},
            )
            .get(
                "us-gaap",
                {},
            )
        )

        for tag in cls.TAG_CANDIDATES.get(
            field_name,
            [],
        ):

            fact = (
                us_gaap.get(
                    tag
                )
            )

            if fact is not None:

                return fact

        return None

    # ========================================================
    # SELECT UNIT ENTRIES
    # ========================================================

    @staticmethod
    def _select_unit_entries(
        fact: dict,
    ) -> list[dict]:

        if not fact:
            return []

        units = fact.get(
            "units",
            {},
        )

        if not units:
            return []

        preferred_units = [
            "USD",
            "USD/shares",
            "USD-per-shares",
        ]

        for unit in preferred_units:

            if unit in units:

                return units[
                    unit
                ]

        first_unit = next(
            iter(units),
            None,
        )

        if first_unit is None:
            return []

        return units[
            first_unit
        ]

    # ========================================================
    # AS-OF FILTER
    #
    # Legacy date-only helper.
    #
    # Existing tests and old callers continue to use this.
    # Precise intraday filtering is handled by
    # _filter_entries_point_in_time().
    # ========================================================

    @staticmethod
    def _as_of_entries(
        entries: list[dict],
        as_of_date: Optional[str],
    ) -> list[dict]:

        if as_of_date is None:

            return list(
                entries
            )

        result = []

        for entry in entries:

            filed = entry.get(
                "filed"
            )

            if filed is None:
                continue

            if (
                filed[:10]
                <= as_of_date[:10]
            ):

                result.append(
                    entry
                )

        return result

    # ========================================================
    # POINT-IN-TIME ENTRY FILTER
    # ========================================================

    def _filter_entries_point_in_time(
        self,
        symbol: str,
        entries: list[dict],
        as_of_value: Optional[str],
        as_of_datetime: Optional[datetime],
    ) -> list[dict]:

        if as_of_datetime is None:

            return self._as_of_entries(
                entries,
                as_of_value,
            )

        result = []

        for entry in entries:

            is_available = self.fundamental_data._entry_is_available(
                symbol=symbol,
                entry=entry,
                as_of_value=as_of_value,
                as_of_datetime=as_of_datetime,
            )

            if not is_available:
                continue

            # ------------------------------------------------
            # Preserve filing timestamp information on the
            # working entry so deduplication can distinguish
            # two amendments submitted on the same calendar
            # day.
            # ------------------------------------------------

            enriched = dict(
                entry
            )

            accession = entry.get(
                "accn"
            )

            metadata = (
                self.fundamental_data
                .get_filing_metadata(
                    symbol=symbol,
                    accession=accession,
                    filing_date=(
                        entry.get("filed")
                    ),
                )
            )

            enriched[
                "_filing_accession"
            ] = (
                metadata.get(
                    "accession_number"
                )
                or accession
            )

            enriched[
                "_acceptance_datetime"
            ] = metadata.get(
                "acceptance_datetime"
            )

            enriched[
                "_filing_form"
            ] = metadata.get(
                "form"
            )

            enriched[
                "_filing_report_date"
            ] = metadata.get(
                "report_date"
            )

            result.append(
                enriched
            )

        return result

    # ========================================================
    # FILING SORT KEY
    # ========================================================

    @staticmethod
    def _filing_sort_key(
            entry: dict,
    ):
        acceptance_datetime = entry.get(
            "_acceptance_datetime",
            "",
        )

        filed = entry.get(
            "filed",
            "",
        )

        accession = entry.get(
            "accn",
            "",
        )

        if not accession:
            accession = entry.get(
                "_filing_accession",
                "",
            )

        return (
            acceptance_datetime,
            filed,
            accession,
        )

    # ========================================================
    # DEDUPLICATE ACTUAL REPORTING PERIOD
    #
    # IMPORTANT:
    # Same start/end = same actual period.
    # Do NOT include fy/fp in identity.
    # ========================================================

    @classmethod
    def _deduplicate_periods(
        cls,
        entries: list[dict],
        as_of_date: Optional[str],
    ) -> list[dict]:

        filtered = cls._as_of_entries(
            entries,
            as_of_date,
        )

        grouped: dict[
            tuple[str, str],
            dict,
        ] = {}

        for entry in filtered:

            start = entry.get(
                "start"
            )

            end = entry.get(
                "end"
            )

            if (
                not start
                or not end
            ):
                continue

            key = (
                start[:10],
                end[:10],
            )

            existing = grouped.get(
                key
            )

            if existing is None:

                grouped[
                    key
                ] = entry

                continue

            existing_key = cls._filing_sort_key(
                existing
            )

            current_key = cls._filing_sort_key(
                entry
            )

            if current_key > existing_key:

                grouped[
                    key
                ] = entry

        return sorted(
            grouped.values(),
            key=lambda item: (
                item.get(
                    "end",
                    "",
                ),
                cls._filing_sort_key(
                    item
                ),
            ),
        )

    # ========================================================
    # QUARTERLY ENTRIES
    # ========================================================

    def _quarterly_entries(
        self,
        fact: dict,
        as_of_date: Optional[str],
        symbol: str = "UNKNOWN",
        as_of_datetime: Optional[datetime] = None,
    ) -> list[dict]:

        entries = (
            self._select_unit_entries(
                fact
            )
        )

        entries = (
            self._filter_entries_point_in_time(
                symbol=symbol,
                entries=entries,
                as_of_value=as_of_date,
                as_of_datetime=as_of_datetime,
            )
        )

        result = []

        for entry in entries:

            days = self._duration_days(
                entry.get(
                    "start"
                ),
                entry.get(
                    "end"
                ),
            )

            if days is None:
                continue

            if (
                self.QUARTER_MIN_DAYS
                <= days
                <= self.QUARTER_MAX_DAYS
            ):

                result.append(
                    entry
                )

        return result

    # ========================================================
    # ANNUAL ENTRIES
    # ========================================================

    def _annual_entries(
        self,
        fact: dict,
        as_of_date: Optional[str],
        symbol: str = "UNKNOWN",
        as_of_datetime: Optional[datetime] = None,
    ) -> list[dict]:

        entries = (
            self._select_unit_entries(
                fact
            )
        )

        entries = (
            self._filter_entries_point_in_time(
                symbol=symbol,
                entries=entries,
                as_of_value=as_of_date,
                as_of_datetime=as_of_datetime,
            )
        )

        annual_candidates = []

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Annual filtering MUST happen before deduplication.
        # ----------------------------------------------------

        for entry in entries:

            start = entry.get(
                "start"
            )

            end = entry.get(
                "end"
            )

            if (
                not start
                or not end
            ):
                continue

            days = self._duration_days(
                start,
                end,
            )

            if days is None:
                continue

            if not (
                self.ANNUAL_MIN_DAYS
                <= days
                <= self.ANNUAL_MAX_DAYS
            ):
                continue

            form = entry.get(
                "form",
                "",
            )

            filing_form = (
                entry.get(
                    "_filing_form"
                )
            )

            if not form:

                form = filing_form or ""

            fiscal_period = entry.get(
                "fp",
                "",
            )

            is_annual_metadata = (
                fiscal_period == "FY"
                or form in {
                    "10-K",
                    "10-K/A",
                    "10-KT",
                    "10-KT/A",
                }
            )

            if not is_annual_metadata:
                continue

            annual_candidates.append(
                entry
            )

        # ----------------------------------------------------
        # Deduplicate actual annual periods.
        # ----------------------------------------------------

        grouped: dict[
            tuple[str, str],
            dict,
        ] = {}

        for entry in annual_candidates:

            key = (
                entry[
                    "start"
                ][:10],
                entry[
                    "end"
                ][:10],
            )

            existing = grouped.get(
                key
            )

            if existing is None:

                grouped[
                    key
                ] = entry

                continue

            existing_key = (
                self._filing_sort_key(
                    existing
                )
            )

            current_key = (
                self._filing_sort_key(
                    entry
                )
            )

            if current_key > existing_key:

                grouped[
                    key
                ] = entry

        return sorted(
            grouped.values(),
            key=lambda item: (
                item.get(
                    "end",
                    "",
                ),
                self._filing_sort_key(
                    item
                ),
            ),
        )

    # ========================================================
    # VALUE
    # ========================================================

    @staticmethod
    def _entry_value(
        entry: Optional[
            dict | float | int
        ],
    ) -> Optional[float]:

        if entry is None:
            return None

        if isinstance(
            entry,
            (int, float),
        ):

            return float(
                entry
            )

        value = entry.get(
            "val"
        )

        if value is None:
            return None

        try:

            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

    # ========================================================
    # PERIOD MAP
    # ========================================================

    @classmethod
    def _period_map(
        cls,
        entries: list[dict],
    ) -> dict[
        tuple[str, str],
        dict,
    ]:

        result = {}

        for entry in entries:

            start = entry.get(
                "start"
            )

            end = entry.get(
                "end"
            )

            if (
                not start
                or not end
            ):
                continue

            result[
                (
                    start[:10],
                    end[:10],
                )
            ] = entry

        return result

    # ========================================================
    # BUILD FIELD MAPS
    # ========================================================

    def _build_field_maps(
        self,
        facts: dict,
        as_of_date: Optional[str],
        symbol: str = "UNKNOWN",
        as_of_datetime: Optional[datetime] = None,
    ):

        quarterly_maps = {}
        annual_maps = {}

        us_gaap = (
            facts
            .get(
                "facts",
                {},
            )
            .get(
                "us-gaap",
                {},
            )
        )

        for field_name, tags in (
            self.TAG_CANDIDATES.items()
        ):

            all_quarterly = []
            all_annual = []

            for tag in tags:

                fact = us_gaap.get(
                    tag
                )

                if fact is None:
                    continue

                all_quarterly.extend(
                    self._quarterly_entries(
                        fact,
                        as_of_date,
                        symbol=symbol,
                        as_of_datetime=(
                            as_of_datetime
                        ),
                    )
                )

                all_annual.extend(
                    self._annual_entries(
                        fact,
                        as_of_date,
                        symbol=symbol,
                        as_of_datetime=(
                            as_of_datetime
                        ),
                    )
                )

            # ------------------------------------------------
            # Merge candidate GAAP tags.
            # ------------------------------------------------

            if as_of_datetime is None:

                all_quarterly = (
                    self._deduplicate_periods(
                        all_quarterly,
                        as_of_date,
                    )
                )

                all_annual = (
                    self._deduplicate_periods(
                        all_annual,
                        as_of_date,
                    )
                )

            else:

                # Entries are already filtered precisely and
                # enriched with acceptance datetime. Deduplicate
                # here without discarding that metadata.
                all_quarterly = (
                    self._deduplicate_precise_entries(
                        all_quarterly
                    )
                )

                all_annual = (
                    self._deduplicate_precise_entries(
                        all_annual
                    )
                )

            quarterly_maps[
                field_name
            ] = self._period_map(
                all_quarterly
            )

            annual_maps[
                field_name
            ] = all_annual

        return (
            quarterly_maps,
            annual_maps,
        )

    # ========================================================
    # PRECISE DEDUPLICATION
    # ========================================================

    @classmethod
    def _deduplicate_precise_entries(
        cls,
        entries: list[dict],
    ) -> list[dict]:

        grouped: dict[
            tuple[str, str],
            dict,
        ] = {}

        for entry in entries:

            start = entry.get(
                "start"
            )

            end = entry.get(
                "end"
            )

            if (
                not start
                or not end
            ):
                continue

            key = (
                start[:10],
                end[:10],
            )

            existing = grouped.get(
                key
            )

            if existing is None:

                grouped[
                    key
                ] = entry

                continue

            if (
                cls._filing_sort_key(
                    entry
                )
                >
                cls._filing_sort_key(
                    existing
                )
            ):

                grouped[
                    key
                ] = entry

        return sorted(
            grouped.values(),
            key=lambda item: (
                item.get(
                    "end",
                    "",
                ),
                cls._filing_sort_key(
                    item
                ),
            ),
        )

    # ========================================================
    # SELECT METADATA
    # ========================================================

    @staticmethod
    def _select_metadata_entry(
        entries: dict[
            str,
            Optional[dict],
        ],
    ) -> Optional[dict]:

        available = [
            entry
            for entry in entries.values()
            if entry is not None
        ]

        if not available:
            return None

        return max(
            available,
            key=(
                FinancialStatementEngine
                ._filing_sort_key
            ),
        )

    # ========================================================
    # BUILD FINANCIAL PERIOD
    # ========================================================

    @staticmethod
    def _build_period_from_values(
        symbol: str,
        start_date: str,
        end_date: str,
        filed_date: str,
        metadata_entry: dict,
        revenue: Optional[float],
        net_income: Optional[float],
        eps: Optional[float],
        operating_cash_flow: Optional[float],
        capital_expenditure: Optional[float],
        free_cash_flow: Optional[float],
        filing_accession: Optional[str] = None,
        filing_acceptance_datetime: Optional[
            str
        ] = None,
    ) -> FinancialPeriod:

        return FinancialPeriod(

            symbol=symbol,

            start_date=start_date[:10],

            end_date=end_date[:10],

            filed_date=filed_date[:10],

            form=metadata_entry.get(
                "form"
            ),

            fiscal_year=metadata_entry.get(
                "fy"
            ),

            fiscal_period=metadata_entry.get(
                "fp"
            ),

            revenue=revenue,

            net_income=net_income,

            eps=eps,

            operating_cash_flow=(
                operating_cash_flow
            ),

            capital_expenditure=(
                capital_expenditure
            ),

            free_cash_flow=(
                free_cash_flow
            ),

            filing_accession=(
                filing_accession
            ),

            filing_acceptance_datetime=(
                filing_acceptance_datetime
            ),
        )

    # ========================================================
    # ANNUAL VALUE BY END DATE
    # ========================================================

    @classmethod
    def _get_value_by_end_date(
        cls,
        entries: list[dict],
        end_date: str,
    ) -> Optional[float]:

        target_end = end_date[:10]

        candidates = []

        for entry in entries:

            entry_end = entry.get(
                "end"
            )

            if (
                entry_end is None
                or entry_end[:10]
                != target_end
            ):
                continue

            candidates.append(
                entry
            )

        if not candidates:
            return None

        annual_candidates = []

        for entry in candidates:

            duration = cls._duration_days(
                entry.get(
                    "start"
                ),
                entry.get(
                    "end"
                ),
            )

            if (
                duration is not None
                and
                cls.ANNUAL_MIN_DAYS
                <= duration
                <= cls.ANNUAL_MAX_DAYS
            ):

                annual_candidates.append(
                    entry
                )

        if annual_candidates:

            candidates = (
                annual_candidates
            )

        selected = max(
            candidates,
            key=cls._filing_sort_key,
        )

        return cls._entry_value(
            selected
        )

    # ========================================================
    # CHECK THREE-QUARTER CONTINUITY
    # ========================================================

    @classmethod
    def _is_continuous_quarter_sequence(
        cls,
        q1: FinancialPeriod,
        q2: FinancialPeriod,
        q3: FinancialPeriod,
        annual_end: str,
    ) -> bool:

        q1_start = cls._parse_date(
            q1.start_date
        )

        q1_end = cls._parse_date(
            q1.end_date
        )

        q2_start = cls._parse_date(
            q2.start_date
        )

        q2_end = cls._parse_date(
            q2.end_date
        )

        q3_start = cls._parse_date(
            q3.start_date
        )

        q3_end = cls._parse_date(
            q3.end_date
        )

        annual_end_date = cls._parse_date(
            annual_end
        )

        if any(
            value is None
            for value in (
                q1_start,
                q1_end,
                q2_start,
                q2_end,
                q3_start,
                q3_end,
                annual_end_date,
            )
        ):

            return False

        durations = [
            cls._duration_days(
                q1.start_date,
                q1.end_date,
            ),

            cls._duration_days(
                q2.start_date,
                q2.end_date,
            ),

            cls._duration_days(
                q3.start_date,
                q3.end_date,
            ),
        ]

        for duration in durations:

            if duration is None:
                return False

            if not (
                cls.QUARTER_MIN_DAYS
                <= duration
                <= cls.QUARTER_MAX_DAYS
            ):

                return False

        # ----------------------------------------------------
        # Quarter endpoints must move forward.
        # ----------------------------------------------------

        if not (
            q1_end
            < q2_end
            < q3_end
        ):

            return False

        # ----------------------------------------------------
        # Quarter starts must follow previous quarter ends.
        # ----------------------------------------------------

        gap_1 = (
            q2_start
            - q1_end
        ).days

        gap_2 = (
            q3_start
            - q2_end
        ).days

        if (
            abs(
                gap_1 - 1
            )
            > cls.QUARTER_GAP_TOLERANCE_DAYS
        ):

            return False

        if (
            abs(
                gap_2 - 1
            )
            > cls.QUARTER_GAP_TOLERANCE_DAYS
        ):

            return False

        if q3_end >= annual_end_date:
            return False

        q3_to_annual = (
            annual_end_date
            - q3_end
        ).days

        if not (
            cls.QUARTER_MIN_DAYS
            <= q3_to_annual
            <= cls.QUARTER_MAX_DAYS
        ):

            return False

        return True

    # ========================================================
    # CHECK FOUR-QUARTER TTM CONTINUITY
    # ========================================================

    @classmethod
    def _is_continuous_ttm_sequence(
        cls,
        periods: list[FinancialPeriod],
    ) -> bool:

        if len(periods) != 4:
            return False

        for period in periods:

            duration = cls._duration_days(
                period.start_date,
                period.end_date,
            )

            if duration is None:
                return False

            if not (
                cls.QUARTER_MIN_DAYS
                <= duration
                <= cls.QUARTER_MAX_DAYS
            ):

                return False

        for previous, current in zip(
            periods,
            periods[1:],
        ):

            previous_end = cls._parse_date(
                previous.end_date
            )

            current_start = cls._parse_date(
                current.start_date
            )

            current_end = cls._parse_date(
                current.end_date
            )

            if (
                previous_end is None
                or current_start is None
                or current_end is None
            ):

                return False

            if current_end <= previous_end:
                return False

            gap = (
                current_start
                - previous_end
            ).days

            if (
                abs(
                    gap - 1
                )
                > cls.QUARTER_GAP_TOLERANCE_DAYS
            ):

                return False

        return True

    # ========================================================
    # SELECT VALID TTM PERIODS
    # ========================================================

    @classmethod
    def _select_ttm_periods(
        cls,
        periods: list[FinancialPeriod],
    ) -> Optional[
        list[FinancialPeriod]
    ]:

        if len(periods) < 4:
            return None

        selected = periods[
            -4:
        ]

        if not cls._is_continuous_ttm_sequence(
            selected
        ):

            return None

        return selected

    # ========================================================
    # FIND Q1/Q2/Q3 FOR ANNUAL PERIOD
    #
    # IMPORTANT:
    # Uses dates, not fy/fp.
    # ========================================================

    @classmethod
    def _find_three_quarters_for_annual(
        cls,
        periods: list[FinancialPeriod],
        annual_end: str,
    ) -> Optional[
        tuple[
            FinancialPeriod,
            FinancialPeriod,
            FinancialPeriod,
        ]
    ]:

        annual_end_date = cls._parse_date(
            annual_end
        )

        if annual_end_date is None:
            return None

        candidates = []

        for period in periods:

            period_end = cls._parse_date(
                period.end_date
            )

            if period_end is None:
                continue

            if period_end >= annual_end_date:
                continue

            duration = cls._duration_days(
                period.start_date,
                period.end_date,
            )

            if duration is None:
                continue

            if not (
                cls.QUARTER_MIN_DAYS
                <= duration
                <= cls.QUARTER_MAX_DAYS
            ):

                continue

            candidates.append(
                period
            )

        candidates.sort(
            key=lambda period: (
                period.end_date,
                period.filed_date,
            )
        )

        if len(candidates) < 3:
            return None

        for index in range(
            len(candidates) - 1,
            1,
            -1,
        ):

            q1 = candidates[
                index - 2
            ]

            q2 = candidates[
                index - 1
            ]

            q3 = candidates[
                index
            ]

            if cls._is_continuous_quarter_sequence(
                q1,
                q2,
                q3,
                annual_end,
            ):

                return (
                    q1,
                    q2,
                    q3,
                )

        return None

    # ========================================================
    # CONVERT RAW TEST RECORD TO FINANCIAL PERIOD
    # ========================================================

    @classmethod
    def _financial_period_from_raw(
        cls,
        raw: dict,
    ) -> FinancialPeriod:

        operating_cash_flow = (
            cls._entry_value(
                raw.get(
                    "_operating_cash_flow"
                )
            )
        )

        capital_expenditure = (
            cls._entry_value(
                raw.get(
                    "_capital_expenditure"
                )
            )
        )

        free_cash_flow = None

        if (
            operating_cash_flow is not None
            and capital_expenditure is not None
        ):

            free_cash_flow = (
                operating_cash_flow
                - capital_expenditure
            )

        return FinancialPeriod(

            symbol=raw.get(
                "symbol",
                "TEST",
            ),

            start_date=raw.get(
                "start",
                "",
            )[:10],

            end_date=raw.get(
                "end",
                "",
            )[:10],

            filed_date=raw.get(
                "filed",
                "1970-01-01",
            )[:10],

            form=raw.get(
                "form"
            ),

            fiscal_year=raw.get(
                "fy"
            ),

            fiscal_period=raw.get(
                "fp"
            ),

            revenue=cls._entry_value(
                raw.get(
                    "_revenue"
                )
            ),

            net_income=cls._entry_value(
                raw.get(
                    "_net_income"
                )
            ),

            eps=cls._entry_value(
                raw.get(
                    "_eps"
                )
            ),

            operating_cash_flow=(
                operating_cash_flow
            ),

            capital_expenditure=(
                capital_expenditure
            ),

            free_cash_flow=(
                free_cash_flow
            ),

            filing_accession=(
                raw.get(
                    "_filing_accession"
                )
                or raw.get(
                    "accn"
                )
            ),

            filing_acceptance_datetime=(
                raw.get(
                    "_acceptance_datetime"
                )
            ),
        )

    # ========================================================
    # DERIVE Q4
    # ========================================================

    @classmethod
    def _derive_q4_entry(
        cls,
        annual_entry: dict,
        q1,
        q2,
        q3,
        annual_values: Optional[
            dict[str, Optional[float]]
        ] = None,
    ):

        if isinstance(
            q1,
            dict,
        ):

            q1 = cls._financial_period_from_raw(
                q1
            )

        if isinstance(
            q2,
            dict,
        ):

            q2 = cls._financial_period_from_raw(
                q2
            )

        if isinstance(
            q3,
            dict,
        ):

            q3 = cls._financial_period_from_raw(
                q3
            )

        if annual_values is None:

            annual_values = {

                "revenue": (
                    cls._entry_value(
                        annual_entry.get(
                            "_revenue"
                        )
                    )
                ),

                "net_income": (
                    cls._entry_value(
                        annual_entry.get(
                            "_net_income"
                        )
                    )
                ),

                "operating_cash_flow": (
                    cls._entry_value(
                        annual_entry.get(
                            "_operating_cash_flow"
                        )
                    )
                ),

                "capital_expenditure": (
                    cls._entry_value(
                        annual_entry.get(
                            "_capital_expenditure"
                        )
                    )
                ),
            }

        annual_start = annual_entry.get(
            "start"
        )

        annual_end = annual_entry.get(
            "end"
        )

        if (
            not annual_start
            or not annual_end
        ):

            return None

        annual_start_date = cls._parse_date(
            annual_start
        )

        annual_end_date = cls._parse_date(
            annual_end
        )

        q3_end_date = cls._parse_date(
            q3.end_date
        )

        if (
            annual_start_date is None
            or annual_end_date is None
            or q3_end_date is None
        ):

            return None

        q4_start_date = (
            q3_end_date
            + timedelta(
                days=1
            )
        )

        if q4_start_date > annual_end_date:
            return None

        # ----------------------------------------------------
        # Validate Q1/Q2/Q3 durations.
        # ----------------------------------------------------

        durations = [

            cls._duration_days(
                q1.start_date,
                q1.end_date,
            ),

            cls._duration_days(
                q2.start_date,
                q2.end_date,
            ),

            cls._duration_days(
                q3.start_date,
                q3.end_date,
            ),
        ]

        for duration in durations:

            if duration is None:
                return None

            if not (
                cls.QUARTER_MIN_DAYS
                <= duration
                <= cls.QUARTER_MAX_DAYS
            ):

                return None

        # ----------------------------------------------------
        # Calculate Q4.
        # ----------------------------------------------------

        def subtract(
            annual: Optional[float],
            first: Optional[float],
            second: Optional[float],
            third: Optional[float],
        ) -> Optional[float]:

            if (
                annual is None
                or first is None
                or second is None
                or third is None
            ):

                return None

            return (
                annual
                - first
                - second
                - third
            )

        revenue = subtract(
            annual_values.get(
                "revenue"
            ),
            q1.revenue,
            q2.revenue,
            q3.revenue,
        )

        net_income = subtract(
            annual_values.get(
                "net_income"
            ),
            q1.net_income,
            q2.net_income,
            q3.net_income,
        )

        operating_cash_flow = subtract(
            annual_values.get(
                "operating_cash_flow"
            ),
            q1.operating_cash_flow,
            q2.operating_cash_flow,
            q3.operating_cash_flow,
        )

        capital_expenditure = subtract(
            annual_values.get(
                "capital_expenditure"
            ),
            q1.capital_expenditure,
            q2.capital_expenditure,
            q3.capital_expenditure,
        )

        free_cash_flow = None

        if (
            operating_cash_flow is not None
            and capital_expenditure is not None
        ):

            free_cash_flow = (
                operating_cash_flow
                - capital_expenditure
            )

        filed_date = annual_entry.get(
            "filed"
        )

        if filed_date is None:
            return None

        return {

            "start": (
                q4_start_date.isoformat()
            ),

            "end": (
                annual_end_date.isoformat()
            ),

            "filed": (
                filed_date[:10]
            ),

            "form": (
                annual_entry.get(
                    "form",
                    "10-K",
                )
                or annual_entry.get(
                    "_filing_form"
                )
                or "10-K"
            ),

            "fy": annual_entry.get(
                "fy"
            ),

            "fp": "Q4",

            "revenue": revenue,

            "net_income": net_income,

            # EPS cannot be safely derived
            "eps": None,

            "operating_cash_flow": (
                operating_cash_flow
            ),

            "capital_expenditure": (
                capital_expenditure
            ),

            "free_cash_flow": (
                free_cash_flow
            ),

            "accn": (
                annual_entry.get(
                    "_filing_accession"
                )
                or annual_entry.get(
                    "accn"
                )
            ),

            "_acceptance_datetime": (
                annual_entry.get(
                    "_acceptance_datetime"
                )
            ),
        }

    # ========================================================
    # QUARTERLY HISTORY
    # ========================================================

    def get_quarterly_history(
        self,
        symbol: str,
        as_of_date: Optional[
            str | date | datetime
        ] = None,
        limit: int = 12,
    ) -> list[FinancialPeriod]:

        symbol = symbol.upper()

        (
            normalized_as_of,
            as_of_datetime,
        ) = self._normalize_as_of(
            as_of_date
        )

        facts = (
            self.fundamental_data
            .get_company_facts(
                symbol
            )
        )

        if facts is None:
            return []

        (
            quarterly_maps,
            annual_maps,
        ) = self._build_field_maps(
            facts=facts,
            as_of_date=normalized_as_of,
            symbol=symbol,
            as_of_datetime=as_of_datetime,
        )

        # ====================================================
        # COLLECT UNIQUE PERIOD KEYS
        # ====================================================

        period_keys: set[
            tuple[str, str]
        ] = set()

        for field_map in (
            quarterly_maps.values()
        ):

            period_keys.update(
                field_map.keys()
            )

        # ====================================================
        # BUILD DIRECT QUARTERS
        # ====================================================

        periods = []

        for (
            start_date,
            end_date,
        ) in sorted(
            period_keys,
            key=lambda key: (
                key[1],
                key[0],
            ),
        ):

            entries = {

                field_name: (
                    quarterly_maps[
                        field_name
                    ].get(
                        (
                            start_date,
                            end_date,
                        )
                    )
                )

                for field_name
                in self.TAG_CANDIDATES
            }

            metadata_entry = (
                self._select_metadata_entry(
                    entries
                )
            )

            if metadata_entry is None:
                continue

            filed_dates = [

                entry.get(
                    "filed"
                )

                for entry
                in entries.values()

                if (
                    entry is not None
                    and entry.get(
                        "filed"
                    ) is not None
                )
            ]

            if not filed_dates:
                continue

            # Latest known field filing.
            filed_date = max(
                filed_dates
            )[:10]

            revenue = (
                self._entry_value(
                    entries[
                        "revenue"
                    ]
                )
            )

            net_income = (
                self._entry_value(
                    entries[
                        "net_income"
                    ]
                )
            )

            eps = (
                self._entry_value(
                    entries[
                        "eps"
                    ]
                )
            )

            operating_cash_flow = (
                self._entry_value(
                    entries[
                        "operating_cash_flow"
                    ]
                )
            )

            capital_expenditure = (
                self._entry_value(
                    entries[
                        "capital_expenditure"
                    ]
                )
            )

            free_cash_flow = None

            if (
                operating_cash_flow is not None
                and capital_expenditure is not None
            ):

                free_cash_flow = (
                    operating_cash_flow
                    - capital_expenditure
                )

            filing_accession = (
                metadata_entry.get(
                    "_filing_accession"
                )
                or metadata_entry.get(
                    "accn"
                )
            )

            filing_acceptance_datetime = (
                metadata_entry.get(
                    "_acceptance_datetime"
                )
            )

            # ------------------------------------------------
            # For date-only calls there may be no enriched
            # metadata. Fetch it once for the selected filing
            # so FinancialPeriod still knows its identity.
            # ------------------------------------------------

            if (
                filing_accession is not None
                and
                filing_acceptance_datetime is None
                and
                as_of_datetime is None
            ):

                metadata = (
                    self.fundamental_data
                    .get_filing_metadata(
                        symbol=symbol,
                        accession=filing_accession,
                        filing_date=filed_date,
                    )
                )

                filing_acceptance_datetime = (
                    metadata.get(
                        "acceptance_datetime"
                    )
                )

            periods.append(
                self._build_period_from_values(

                    symbol=symbol,

                    start_date=start_date,

                    end_date=end_date,

                    filed_date=filed_date,

                    metadata_entry=metadata_entry,

                    revenue=revenue,

                    net_income=net_income,

                    eps=eps,

                    operating_cash_flow=(
                        operating_cash_flow
                    ),

                    capital_expenditure=(
                        capital_expenditure
                    ),

                    free_cash_flow=(
                        free_cash_flow
                    ),

                    filing_accession=(
                        filing_accession
                    ),

                    filing_acceptance_datetime=(
                        filing_acceptance_datetime
                    ),
                )
            )

        # ====================================================
        # DERIVE MISSING Q4
        # ====================================================

        annual_end_dates = set()

        for entries in (
            annual_maps.values()
        ):

            for entry in entries:

                end = entry.get(
                    "end"
                )

                if end is None:
                    continue

                annual_end_dates.add(
                    end[:10]
                )

        for annual_end in sorted(
            annual_end_dates
        ):

            already_exists = any(
                period.end_date
                == annual_end
                for period in periods
            )

            if already_exists:
                continue

            three_quarters = (
                self._find_three_quarters_for_annual(
                    periods=periods,
                    annual_end=annual_end,
                )
            )

            if three_quarters is None:
                continue

            q1, q2, q3 = three_quarters

            # ------------------------------------------------
            # Annual revenue entry
            # ------------------------------------------------

            annual_revenue_entry = None

            revenue_annual_entries = (
                annual_maps.get(
                    "revenue",
                    []
                )
            )

            for entry in revenue_annual_entries:

                entry_end = entry.get(
                    "end"
                )

                if (
                    entry_end is not None
                    and entry_end[:10]
                    == annual_end
                ):

                    annual_revenue_entry = entry
                    break

            annual_entry = (
                annual_revenue_entry
            )

            if annual_entry is None:

                for field_name in (
                    self.TAG_CANDIDATES
                ):

                    candidates = (
                        annual_maps.get(
                            field_name,
                            []
                        )
                    )

                    for entry in candidates:

                        entry_end = (
                            entry.get(
                                "end"
                            )
                        )

                        if (
                            entry_end is not None
                            and entry_end[:10]
                            == annual_end
                        ):

                            annual_entry = entry
                            break

                    if annual_entry is not None:
                        break

            if annual_entry is None:
                continue

            # ------------------------------------------------
            # Annual values
            # ------------------------------------------------

            annual_values = {

                "revenue": (
                    self._get_value_by_end_date(
                        annual_maps.get(
                            "revenue",
                            []
                        ),
                        annual_end,
                    )
                ),

                "net_income": (
                    self._get_value_by_end_date(
                        annual_maps.get(
                            "net_income",
                            []
                        ),
                        annual_end,
                    )
                ),

                "operating_cash_flow": (
                    self._get_value_by_end_date(
                        annual_maps.get(
                            "operating_cash_flow",
                            []
                        ),
                        annual_end,
                    )
                ),

                "capital_expenditure": (
                    self._get_value_by_end_date(
                        annual_maps.get(
                            "capital_expenditure",
                            []
                        ),
                        annual_end,
                    )
                ),
            }

            # Revenue is still the primary anchor.
            if (
                annual_values[
                    "revenue"
                ]
                is None
            ):

                continue

            q4 = self._derive_q4_entry(
                annual_entry=annual_entry,
                q1=q1,
                q2=q2,
                q3=q3,
                annual_values=annual_values,
            )

            if q4 is None:
                continue

            periods.append(
                FinancialPeriod(

                    symbol=symbol,

                    start_date=q4[
                        "start"
                    ],

                    end_date=q4[
                        "end"
                    ],

                    filed_date=q4[
                        "filed"
                    ],

                    form=q4[
                        "form"
                    ],

                    fiscal_year=q4[
                        "fy"
                    ],

                    fiscal_period=q4[
                        "fp"
                    ],

                    revenue=q4[
                        "revenue"
                    ],

                    net_income=q4[
                        "net_income"
                    ],

                    eps=q4[
                        "eps"
                    ],

                    operating_cash_flow=q4[
                        "operating_cash_flow"
                    ],

                    capital_expenditure=q4[
                        "capital_expenditure"
                    ],

                    free_cash_flow=q4[
                        "free_cash_flow"
                    ],

                    filing_accession=q4.get(
                        "accn"
                    ),

                    filing_acceptance_datetime=(
                        q4.get(
                            "_acceptance_datetime"
                        )
                    ),
                )
            )

        # ====================================================
        # FINAL SORT
        # ====================================================

        periods.sort(
            key=lambda period: (
                period.end_date,
                period.filed_date,
            )
        )

        # ====================================================
        # FINAL UNIQUE PERIODS
        # ====================================================

        unique_periods: dict[
            tuple[str, str],
            FinancialPeriod,
        ] = {}

        for period in periods:

            key = (
                period.start_date,
                period.end_date,
            )

            existing = (
                unique_periods.get(
                    key
                )
            )

            if existing is None:

                unique_periods[
                    key
                ] = period

                continue

            current_key = (
                period.filing_acceptance_datetime
                or period.filed_date
                or ""
            )

            existing_key = (
                existing.filing_acceptance_datetime
                or existing.filed_date
                or ""
            )

            if current_key > existing_key:

                unique_periods[
                    key
                ] = period

        periods = sorted(
            unique_periods.values(),
            key=lambda period: (
                period.end_date,
                period.filed_date,
            )
        )

        return periods[
            -limit:
        ]

    # ========================================================
    # TTM SUM
    # ========================================================

    @classmethod
    def _ttm_sum(
        cls,
        periods: list[FinancialPeriod],
        field_name: str,
    ) -> Optional[float]:

        selected = (
            cls._select_ttm_periods(
                periods
            )
        )

        if selected is None:
            return None

        values = []

        for period in selected:

            value = getattr(
                period,
                field_name,
                None,
            )

            if value is None:
                return None

            values.append(
                float(value)
            )

        return sum(
            values
        )

    # ========================================================
    # GROWTH
    #
    # Sign-aware:
    #
    # positive -> positive:
    #     standard percentage growth
    #
    # negative -> negative:
    #     improvement is positive when the loss becomes smaller
    #
    # negative -> positive or positive -> negative:
    #     return None because ordinary percentage growth is not
    #     economically meaningful across a zero crossing.
    # ========================================================

    @staticmethod
    def _growth(
        current: Optional[float],
        previous: Optional[float],
    ) -> Optional[float]:

        if current is None:
            return None

        if previous is None:
            return None

        if previous == 0:
            return None

        # ----------------------------------------------------
        # Standard positive -> positive case
        # ----------------------------------------------------

        if (
            previous > 0
            and current >= 0
        ):

            return (
                current
                / previous
            ) - 1.0

        # ----------------------------------------------------
        # Negative -> negative
        #
        # Example:
        #     -100 -> -50
        #
        # Result:
        #     +50%
        #
        # Example:
        #     -100 -> -120
        #
        # Result:
        #     -20%
        # ----------------------------------------------------

        if (
            previous < 0
            and current <= 0
        ):

            return (
                abs(previous)
                - abs(current)
            ) / abs(previous)

        # ----------------------------------------------------
        # Negative -> zero
        # ----------------------------------------------------

        if (
            previous < 0
            and current == 0
        ):

            return 1.0

        # ----------------------------------------------------
        # Positive -> zero
        # ----------------------------------------------------

        if (
            previous > 0
            and current == 0
        ):

            return -1.0

        # ----------------------------------------------------
        # Zero crossing:
        #
        # We deliberately do not manufacture a percentage.
        # ----------------------------------------------------

        return None

    # ========================================================
    # SAME-QUARTER YEAR-AGO VALIDATION
    # ========================================================

    @classmethod
    def _is_year_ago_quarter(
        cls,
        latest: FinancialPeriod,
        year_ago: FinancialPeriod,
    ) -> bool:

        latest_end = cls._parse_date(
            latest.end_date
        )

        year_ago_end = cls._parse_date(
            year_ago.end_date
        )

        if (
            latest_end is None
            or year_ago_end is None
        ):

            return False

        delta = (
            latest_end
            - year_ago_end
        ).days

        return (
            300
            <= delta
            <= 380
        )

    # ========================================================
    # TTM
    # ========================================================

    def get_ttm(
        self,
        symbol: str,
        as_of_date: Optional[
            str | date | datetime
        ] = None,
    ) -> Optional[
        TTMFinancials
    ]:

        periods = (
            self.get_quarterly_history(
                symbol=symbol,
                as_of_date=as_of_date,
                limit=12,
            )
        )

        selected = (
            self._select_ttm_periods(
                periods
            )
        )

        if selected is None:
            return None

        latest = selected[
            -1
        ]

        previous_quarter = selected[
            -2
        ]

        # ----------------------------------------------------
        # TTM additive fields
        # ----------------------------------------------------

        revenue_ttm = self._ttm_sum(
            periods,
            "revenue",
        )

        net_income_ttm = self._ttm_sum(
            periods,
            "net_income",
        )

        eps_ttm = self._ttm_sum(
            periods,
            "eps",
        )

        operating_cash_flow_ttm = (
            self._ttm_sum(
                periods,
                "operating_cash_flow",
            )
        )

        capital_expenditure_ttm = (
            self._ttm_sum(
                periods,
                "capital_expenditure",
            )
        )

        free_cash_flow_ttm = (
            self._ttm_sum(
                periods,
                "free_cash_flow",
            )
        )

        # ====================================================
        # QoQ
        # ====================================================

        revenue_qoq = self._growth(
            latest.revenue,
            previous_quarter.revenue,
        )

        net_income_qoq = self._growth(
            latest.net_income,
            previous_quarter.net_income,
        )

        eps_qoq = self._growth(
            latest.eps,
            previous_quarter.eps,
        )

        # ====================================================
        # YoY
        # ====================================================

        revenue_yoy = None
        net_income_yoy = None
        eps_yoy = None
        fcf_yoy = None

        year_ago_quarter = None

        if len(periods) >= 5:

            candidate = periods[
                -5
            ]

            if self._is_year_ago_quarter(
                latest,
                candidate,
            ):

                year_ago_quarter = (
                    candidate
                )

        if year_ago_quarter is not None:

            revenue_yoy = self._growth(
                latest.revenue,
                year_ago_quarter.revenue,
            )

            net_income_yoy = self._growth(
                latest.net_income,
                year_ago_quarter.net_income,
            )

            eps_yoy = self._growth(
                latest.eps,
                year_ago_quarter.eps,
            )

            fcf_yoy = self._growth(
                latest.free_cash_flow,
                year_ago_quarter.free_cash_flow,
            )

        return TTMFinancials(

            symbol=symbol.upper(),

            as_of_date=(
                self._normalize_date(
                    as_of_date
                )
            ),

            latest_quarter_end=(
                latest.end_date
            ),

            revenue_ttm=revenue_ttm,

            net_income_ttm=(
                net_income_ttm
            ),

            eps_ttm=eps_ttm,

            operating_cash_flow_ttm=(
                operating_cash_flow_ttm
            ),

            capital_expenditure_ttm=(
                capital_expenditure_ttm
            ),

            free_cash_flow_ttm=(
                free_cash_flow_ttm
            ),

            revenue_qoq=revenue_qoq,

            revenue_yoy=revenue_yoy,

            net_income_qoq=(
                net_income_qoq
            ),

            net_income_yoy=(
                net_income_yoy
            ),

            eps_qoq=eps_qoq,

            eps_yoy=eps_yoy,

            fcf_yoy=fcf_yoy,

            latest_filing_accession=(
                latest.filing_accession
            ),

            latest_filing_acceptance_datetime=(
                latest.filing_acceptance_datetime
            ),
        )