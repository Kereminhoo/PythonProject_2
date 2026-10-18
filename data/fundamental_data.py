from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

import requests


# ============================================================
# FUNDAMENTAL SNAPSHOT
# ============================================================

@dataclass
class FundamentalSnapshot:

    symbol: str

    # Point-in-time information
    as_of_date: Optional[str]
    report_date: Optional[str]
    filing_date: Optional[str]

    # Raw filing identity
    filing_accession: Optional[str] = None
    filing_acceptance_datetime: Optional[str] = None

    # Raw financial statement values
    revenue: Optional[float] = None
    net_income: Optional[float] = None

    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    stockholders_equity: Optional[float] = None

    cash: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capital_expenditure: Optional[float] = None

    eps: Optional[float] = None

    # Derived ratios
    net_margin: Optional[float] = None
    return_on_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    cash_to_assets: Optional[float] = None
    free_cash_flow: Optional[float] = None
    free_cash_flow_margin: Optional[float] = None


# ============================================================
# FUNDAMENTAL DATA ENGINE
# ============================================================

class FundamentalData:

    SEC_BASE_URL = (
        "https://data.sec.gov"
    )

    COMPANY_FACTS_URL = (
        SEC_BASE_URL
        + "/api/xbrl/companyfacts/CIK{cik}.json"
    )

    SUBMISSIONS_URL = (
        SEC_BASE_URL
        + "/submissions/CIK{cik}.json"
    )

    # ========================================================
    # TICKER -> CIK
    # ========================================================

    TICKER_TO_CIK = {

        "AAPL": "0000320193",
        "MSFT": "0000789019",
        "NVDA": "0001045810",
        "AMZN": "0001018724",
        "META": "0001326801",
        "GOOGL": "0001652044",
        "GOOG": "0001652044",
        "AVGO": "0001730168",
        "TSLA": "0001318605",
        "AMD": "0000002488",
        "NFLX": "0001065280",
        "ORCL": "0001341439",
        "ADBE": "0000796343",
        "CRM": "0001108524",
        "QCOM": "0000804328",
        "JPM": "0000019617",
        "V": "0001403161",
        "MA": "0001141391",
        "XOM": "0000034088",
        "CVX": "0000093410",
        "WMT": "0000104169",
        "COST": "0000909832",
        "KO": "0000021344",
        "PEP": "0000077476",
        "SPY": None,
    }

    # ========================================================
    # XBRL TAG CANDIDATES
    # ========================================================

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

        "total_assets": [
            "Assets",
        ],

        "total_liabilities": [
            "Liabilities",
        ],

        "stockholders_equity": [
            "StockholdersEquity",
            (
                "StockholdersEquityIncludingPortion"
                "AttributableToNoncontrollingInterest"
            ),
        ],

        "cash": [
            "CashAndCashEquivalentsAtCarryingValue",
        ],

        "operating_cash_flow": [
            "NetCashProvidedByUsedInOperatingActivities",
        ],

        "capital_expenditure": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
        ],

        "eps": [
            "EarningsPerShareDiluted",
            "EarningsPerShareBasic",
        ],
    }

    # ========================================================
    # FORM TYPES
    # ========================================================

    ANNUAL_FORMS = {
        "10-K",
        "10-K/A",
        "10-KT",
        "10-KT/A",
    }

    QUARTERLY_FORMS = {
        "10-Q",
        "10-Q/A",
    }

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        settings=None,
        user_agent: str = (
            "QuantTradingResearch "
            "contact@example.com"
        ),
    ):

        self.settings = settings

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Encoding": (
                    "gzip, deflate"
                ),
            }
        )

        # ----------------------------------------------------
        # Company Facts cache
        # ----------------------------------------------------

        self._facts_cache: dict[
            str,
            dict,
        ] = {}

        # ----------------------------------------------------
        # SEC submissions cache
        #
        # Key:
        #     symbol
        #
        # Value:
        #     submissions JSON
        # ----------------------------------------------------

        self._submissions_cache: dict[
            str,
            dict,
        ] = {}

        # ----------------------------------------------------
        # Older submission file cache
        # ----------------------------------------------------

        self._submission_file_cache: dict[
            str,
            dict,
        ] = {}

        # ----------------------------------------------------
        # Filing metadata cache
        #
        # Key:
        #     normalized accession
        #
        # Value:
        #     filing metadata dictionary
        # ----------------------------------------------------

        self._filing_metadata_cache: dict[
            str,
            dict,
        ] = {}

    # ========================================================
    # DATE NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_date(
        value: Optional[
            str | date | datetime
        ],
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
            value: Optional[
                str | date | datetime
                ],
    ) -> tuple[
        Optional[str],
        Optional[datetime],
    ]:

        if value is None:
            return None, None

        # ----------------------------------------------------
        # datetime object
        # ----------------------------------------------------

        if isinstance(
                value,
                datetime,
        ):

            dt = value

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            else:

                dt = dt.astimezone(
                    timezone.utc
                )

            return (
                dt.isoformat(),
                dt,
            )

        # ----------------------------------------------------
        # date object
        #
        # datetime is checked above because datetime is also
        # a subclass of date.
        # ----------------------------------------------------

        if isinstance(
                value,
                date,
        ):
            return (
                value.isoformat(),
                None,
            )

        # ----------------------------------------------------
        # string
        # ----------------------------------------------------

        text = str(value).strip()

        if not text:
            return None, None

        # ----------------------------------------------------
        # DATE-ONLY STRING
        #
        # "2025-01-15" must remain date-only.
        # It must NOT become 00:00 UTC.
        # ----------------------------------------------------

        try:

            parsed_date = date.fromisoformat(
                text
            )

            return (
                parsed_date.isoformat(),
                None,
            )

        except ValueError:
            pass

        # ----------------------------------------------------
        # ISO DATETIME
        # ----------------------------------------------------

        try:

            normalized_text = text

            if normalized_text.endswith(
                    "Z"
            ):
                normalized_text = (
                        normalized_text[:-1]
                        + "+00:00"
                )

            dt = datetime.fromisoformat(
                normalized_text
            )

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            else:

                dt = dt.astimezone(
                    timezone.utc
                )

            return (
                dt.isoformat(),
                dt,
            )

        except ValueError:

            return (
                text[:10],
                None,
            )

    # ========================================================
    # NORMALIZE DATETIME
    # ========================================================

    @staticmethod
    def _normalize_datetime(
        value: Optional[str | datetime],
    ) -> Optional[datetime]:

        if value is None:
            return None

        if isinstance(
            value,
            datetime,
        ):

            dt = value

        else:

            text = str(value).strip()

            if text.endswith("Z"):
                text = (
                    text[:-1]
                    + "+00:00"
                )

            try:

                dt = datetime.fromisoformat(
                    text
                )

            except ValueError:

                return None

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        else:

            dt = dt.astimezone(
                timezone.utc
            )

        return dt

    # ========================================================
    # CIK
    # ========================================================

    def get_cik(
        self,
        symbol: str,
    ) -> Optional[str]:

        return self.TICKER_TO_CIK.get(
            symbol.upper()
        )

    # ========================================================
    # COMPANY FACTS
    # ========================================================

    def get_company_facts(
        self,
        symbol: str,
    ) -> Optional[dict]:

        symbol = symbol.upper()

        if symbol in self._facts_cache:

            return self._facts_cache[
                symbol
            ]

        cik = self.get_cik(
            symbol
        )

        if cik is None:
            return None

        url = (
            self.COMPANY_FACTS_URL.format(
                cik=cik
            )
        )

        response = self.session.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        self._facts_cache[
            symbol
        ] = data

        return data

    # ========================================================
    # SEC SUBMISSIONS
    # ========================================================

    def get_submissions(
        self,
        symbol: str,
    ) -> Optional[dict]:

        symbol = symbol.upper()

        if symbol in self._submissions_cache:

            return self._submissions_cache[
                symbol
            ]

        cik = self.get_cik(
            symbol
        )

        if cik is None:
            return None

        url = (
            self.SUBMISSIONS_URL.format(
                cik=cik
            )
        )

        response = self.session.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        self._submissions_cache[
            symbol
        ] = data

        return data

    # ========================================================
    # ACCESSION NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_accession(
        accession: Optional[str],
    ) -> Optional[str]:

        if accession is None:
            return None

        return (
            str(accession)
            .strip()
            .replace("-", "")
        )

    # ========================================================
    # SUBMISSION BLOCK -> RECORDS
    #
    # SEC stores filing history in a compact columnar
    # structure. Convert it to ordinary row dictionaries.
    # ========================================================

    @classmethod
    def _submission_block_to_records(
        cls,
        block: Optional[dict],
    ) -> list[dict]:

        if not block:
            return []

        accession_numbers = (
            block.get(
                "accessionNumber",
                [],
            )
        )

        field_names = [
            "accessionNumber",
            "filingDate",
            "reportDate",
            "acceptanceDateTime",
            "form",
            "primaryDocument",
            "primaryDocDescription",
            "items",
            "fileNumber",
            "filmNumber",
        ]

        record_count = len(
            accession_numbers
        )

        records = []

        for index in range(
            record_count
        ):

            record = {}

            for field_name in field_names:

                values = block.get(
                    field_name,
                    [],
                )

                if index < len(values):

                    record[
                        field_name
                    ] = values[index]

                else:

                    record[
                        field_name
                    ] = None

            records.append(
                record
            )

        return records

    # ========================================================
    # LOAD ADDITIONAL SUBMISSION FILE
    # ========================================================

    def _get_submission_file(
        self,
        file_name: str,
    ) -> Optional[dict]:

        if (
            file_name
            in self._submission_file_cache
        ):

            return (
                self._submission_file_cache[
                    file_name
                ]
            )

        url = (
            self.SEC_BASE_URL
            + "/submissions/"
            + file_name
        )

        response = self.session.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        self._submission_file_cache[
            file_name
        ] = data

        return data

    # ========================================================
    # FIND SUBMISSION RECORD
    # ========================================================

    def _find_submission_record(
        self,
        symbol: str,
        accession: Optional[str],
        filing_date: Optional[str] = None,
    ) -> Optional[dict]:

        normalized_accession = (
            self._normalize_accession(
                accession
            )
        )

        if normalized_accession is None:
            return None

        submissions = self.get_submissions(
            symbol
        )

        if submissions is None:
            return None

        # ----------------------------------------------------
        # Check recent filings
        # ----------------------------------------------------

        recent = (
            submissions
            .get("filings", {})
            .get("recent", {})
        )

        recent_records = (
            self._submission_block_to_records(
                recent
            )
        )

        for record in recent_records:

            record_accession = (
                self._normalize_accession(
                    record.get(
                        "accessionNumber"
                    )
                )
            )

            if (
                record_accession
                == normalized_accession
            ):

                return record

        # ----------------------------------------------------
        # Check older submission files.
        #
        # We first use the filing date, when available, to
        # avoid downloading irrelevant historical files.
        # ----------------------------------------------------

        additional_files = (
            submissions
            .get("filings", {})
            .get("files", [])
        )

        target_date = None

        if filing_date:

            target_date = (
                self._normalize_date(
                    filing_date
                )
            )

        for file_info in additional_files:

            file_name = file_info.get(
                "name"
            )

            if not file_name:
                continue

            filing_from = (
                file_info.get(
                    "filingFrom"
                )
            )

            filing_to = (
                file_info.get(
                    "filingTo"
                )
            )

            if target_date:

                if (
                    filing_from
                    and target_date
                    < filing_from
                ):
                    continue

                if (
                    filing_to
                    and target_date
                    > filing_to
                ):
                    continue

            data = (
                self._get_submission_file(
                    file_name
                )
            )

            if data is None:
                continue

            # Older files normally contain the same
            # columnar structure directly.
            records = (
                self._submission_block_to_records(
                    data
                )
            )

            for record in records:

                record_accession = (
                    self._normalize_accession(
                        record.get(
                            "accessionNumber"
                        )
                    )
                )

                if (
                    record_accession
                    == normalized_accession
                ):

                    return record

        return None

    # ========================================================
    # FILING METADATA
    # ========================================================

    def get_filing_metadata(
        self,
        symbol: str,
        accession: Optional[str],
        filing_date: Optional[str] = None,
    ) -> dict:

        normalized_accession = (
            self._normalize_accession(
                accession
            )
        )

        if normalized_accession is None:

            return {
                "accession_number": None,
                "filing_date": filing_date,
                "acceptance_datetime": None,
                "report_date": None,
                "form": None,
                "primary_document": None,
            }

        cached = (
            self._filing_metadata_cache.get(
                normalized_accession
            )
        )

        if cached is not None:
            return cached

        record = (
            self._find_submission_record(
                symbol=symbol,
                accession=accession,
                filing_date=filing_date,
            )
        )

        if record is None:

            metadata = {
                "accession_number": (
                    accession
                ),
                "filing_date": (
                    filing_date
                ),
                "acceptance_datetime": None,
                "report_date": None,
                "form": None,
                "primary_document": None,
            }

            self._filing_metadata_cache[
                normalized_accession
            ] = metadata

            return metadata

        metadata = {
            "accession_number": (
                record.get(
                    "accessionNumber"
                )
            ),

            "filing_date": (
                record.get(
                    "filingDate"
                )
            ),

            "acceptance_datetime": (
                record.get(
                    "acceptanceDateTime"
                )
            ),

            "report_date": (
                record.get(
                    "reportDate"
                )
            ),

            "form": (
                record.get(
                    "form"
                )
            ),

            "primary_document": (
                record.get(
                    "primaryDocument"
                )
            ),
        }

        self._filing_metadata_cache[
            normalized_accession
        ] = metadata

        return metadata

    # ========================================================
    # ENTRY FILING IDENTITY
    # ========================================================

    @staticmethod
    def _entry_filing_identity(
        entry: dict,
    ) -> tuple[str, str]:

        accession = (
            entry.get("accn")
        )

        normalized_accession = (
            FundamentalData
            ._normalize_accession(
                accession
            )
        )

        if normalized_accession:

            return (
                "accession",
                normalized_accession,
            )

        # ----------------------------------------------------
        # Fallback for synthetic tests or old records that do
        # not expose accession number.
        # ----------------------------------------------------

        filed = (
            entry.get(
                "filed",
                "",
            )
        )

        form = (
            entry.get(
                "form",
                "",
            )
        )

        return (
            "filed",
            f"{filed}|{form}",
        )

    # ========================================================
    # ENTRY POINT-IN-TIME AVAILABILITY
    # ========================================================

    def _entry_is_available(
        self,
        symbol: str,
        entry: dict,
        as_of_value: Optional[str],
        as_of_datetime: Optional[datetime],
    ) -> bool:

        filed = entry.get(
            "filed"
        )

        if filed is None:
            return False

        # ----------------------------------------------------
        # Date-only cutoff.
        #
        # Existing behavior remains compatible.
        # ----------------------------------------------------

        if as_of_datetime is None:

            if as_of_value is None:
                return True

            return (
                filed[:10]
                <= as_of_value[:10]
            )

        # ----------------------------------------------------
        # Exact datetime cutoff.
        # ----------------------------------------------------

        accession = entry.get(
            "accn"
        )

        metadata = (
            self.get_filing_metadata(
                symbol=symbol,
                accession=accession,
                filing_date=(
                    filed[:10]
                ),
            )
        )

        acceptance_datetime = (
            self._normalize_datetime(
                metadata.get(
                    "acceptance_datetime"
                )
            )
        )

        if acceptance_datetime is not None:

            return (
                acceptance_datetime
                <= as_of_datetime
            )

        # ----------------------------------------------------
        # Conservative fallback.
        #
        # If exact acceptance time is unavailable, a filing
        # published on the SAME DAY is NOT treated as known for
        # an intraday cutoff.
        #
        # A filing from an earlier day is allowed.
        # ----------------------------------------------------

        try:

            filed_date = (
                date.fromisoformat(
                    filed[:10]
                )
            )

        except ValueError:

            return False

        return (
            filed_date
            < as_of_datetime.date()
        )

    # ========================================================
    # FIND FACT
    # ========================================================

    @classmethod
    def _find_fact(
        cls,
        facts: dict,
        tags: list[str],
    ) -> Optional[dict]:

        us_gaap = (
            facts
            .get("facts", {})
            .get("us-gaap", {})
        )

        for tag in tags:

            fact = (
                us_gaap.get(tag)
            )

            if fact is not None:

                return fact

        return None

    # ========================================================
    # ITERATE FACT ENTRIES
    # ========================================================

    @classmethod
    def _iter_fact_entries(
        cls,
        facts: dict,
        field_name: str,
    ):

        us_gaap = (
            facts
            .get("facts", {})
            .get("us-gaap", {})
        )

        tags = cls.TAG_CANDIDATES.get(
            field_name,
            [],
        )

        for tag in tags:

            fact = (
                us_gaap.get(tag)
            )

            if fact is None:
                continue

            units = fact.get(
                "units",
                {},
            )

            for unit_name, unit_entries in (
                units.items()
            ):

                for entry in unit_entries:

                    normalized = dict(
                        entry
                    )

                    normalized[
                        "_unit"
                    ] = unit_name

                    normalized[
                        "_tag"
                    ] = tag

                    yield normalized

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
    # Legacy helper.
    #
    # This function intentionally remains date-based because
    # existing FinancialStatementEngine code still uses it.
    # Precise datetime filtering is performed by
    # _entry_is_available() in snapshot construction.
    # ========================================================

    @staticmethod
    def _as_of_entries(
        entries: list[dict],
        as_of_date: Optional[str],
    ) -> list[dict]:

        if as_of_date is None:
            return list(entries)

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
    # SELECT LATEST ENTRY
    #
    # Legacy helper used by existing tests and callers.
    # ========================================================

    @classmethod
    def _select_latest_entry(
        cls,
        fact: dict,
        as_of_date: Optional[str] = None,
    ) -> Optional[dict]:

        if not fact:
            return None

        units = fact.get(
            "units",
            {},
        )

        if not units:
            return None

        entries = []

        for unit_name, unit_entries in (
            units.items()
        ):

            for entry in unit_entries:

                filing_date = (
                    entry.get(
                        "filed"
                    )
                )

                if filing_date is None:
                    continue

                if (
                    as_of_date is not None
                    and filing_date[:10]
                    > as_of_date[:10]
                ):

                    continue

                normalized = dict(
                    entry
                )

                normalized[
                    "_unit"
                ] = unit_name

                entries.append(
                    normalized
                )

        if not entries:
            return None

        entries.sort(
            key=lambda item: (
                item.get(
                    "filed",
                    "",
                ),
                item.get(
                    "end",
                    "",
                ),
            )
        )

        return entries[-1]

    # ========================================================
    # EXTRACT LATEST VALUE
    # ========================================================

    @classmethod
    def _extract_latest_value(
        cls,
        fact: dict,
        as_of_date: Optional[str] = None,
    ):

        entry = (
            cls._select_latest_entry(
                fact,
                as_of_date=as_of_date,
            )
        )

        if entry is None:

            return (
                None,
                None,
                None,
            )

        return (
            entry.get("val"),
            entry.get("end"),
            entry.get("filed"),
        )

    # ========================================================
    # GET FIELD VALUE
    # ========================================================

    def _get_fact_value(
        self,
        facts: dict,
        field_name: str,
        as_of_date: Optional[str] = None,
    ):

        tags = self.TAG_CANDIDATES.get(
            field_name,
            [],
        )

        fact = self._find_fact(
            facts,
            tags,
        )

        if fact is None:

            return (
                None,
                None,
                None,
            )

        return self._extract_latest_value(
            fact,
            as_of_date=as_of_date,
        )

    # ========================================================
    # SAFE DIVIDE
    # ========================================================

    @staticmethod
    def _safe_divide(
        numerator: Optional[float],
        denominator: Optional[float],
    ) -> Optional[float]:

        if numerator is None:
            return None

        if denominator is None:
            return None

        if denominator == 0:
            return None

        return (
            numerator
            / denominator
        )

    # ========================================================
    # SELECT LATEST AVAILABLE FILING
    #
    # This is the core point-in-time snapshot mechanism.
    #
    # We first find the latest filing/accession that is known
    # at the requested cutoff.
    #
    # We then extract all fields from THAT SAME filing.
    # ========================================================

    def _select_latest_available_filing(
        self,
        symbol: str,
        facts: dict,
        as_of_value: Optional[str],
        as_of_datetime: Optional[datetime],
    ) -> Optional[dict]:

        filings: dict[
            tuple[str, str],
            dict,
        ] = {}

        for field_name in (
            self.TAG_CANDIDATES
        ):

            for entry in (
                self._iter_fact_entries(
                    facts,
                    field_name,
                )
            ):

                if not self._entry_is_available(
                    symbol=symbol,
                    entry=entry,
                    as_of_value=as_of_value,
                    as_of_datetime=as_of_datetime,
                ):

                    continue

                identity = (
                    self._entry_filing_identity(
                        entry
                    )
                )

                candidate = filings.get(
                    identity
                )

                if candidate is None:

                    metadata = (
                        self.get_filing_metadata(
                            symbol=symbol,
                            accession=(
                                entry.get(
                                    "accn"
                                )
                            ),
                            filing_date=(
                                entry.get(
                                    "filed"
                                )
                            ),
                        )
                    )

                    candidate = {
                        "identity": identity,
                        "accession": (
                            entry.get(
                                "accn"
                            )
                        ),
                        "filing_date": (
                            entry.get(
                                "filed"
                            )
                        ),
                        "acceptance_datetime": (
                            metadata.get(
                                "acceptance_datetime"
                            )
                        ),
                        "report_date": (
                            metadata.get(
                                "report_date"
                            )
                        ),
                        "form": (
                            metadata.get(
                                "form"
                            )
                            or entry.get(
                                "form"
                            )
                        ),
                        "field_names": set(),
                    }

                    filings[
                        identity
                    ] = candidate

                candidate[
                    "field_names"
                ].add(
                    field_name
                )

        if not filings:
            return None

        # ----------------------------------------------------
        # Sort primarily by exact acceptance time when known.
        # Fall back to filed date.
        # ----------------------------------------------------

        def sort_key(
            candidate: dict,
        ):

            acceptance_datetime = (
                self._normalize_datetime(
                    candidate.get(
                        "acceptance_datetime"
                    )
                )
            )

            if (
                acceptance_datetime
                is not None
            ):

                time_key = (
                    2,
                    acceptance_datetime,
                )

            else:

                filing_date = (
                    candidate.get(
                        "filing_date"
                    )
                    or ""
                )

                time_key = (
                    1,
                    filing_date,
                )

            return (
                time_key,
                len(
                    candidate[
                        "field_names"
                    ]
                ),
                candidate.get(
                    "accession"
                )
                or "",
            )

        return max(
            filings.values(),
            key=sort_key,
        )

    # ========================================================
    # ENTRY MATCHES FILING
    # ========================================================

    @classmethod
    def _entry_matches_filing(
        cls,
        entry: dict,
        filing: dict,
    ) -> bool:

        identity = (
            cls._entry_filing_identity(
                entry
            )
        )

        return (
            identity
            == filing[
                "identity"
            ]
        )

    # ========================================================
    # SELECT ENTRY FROM SAME FILING
    #
    # When a single filing contains multiple contexts for the
    # same XBRL concept, prefer the latest report-end date and,
    # for duration facts, prefer the period matching the filing
    # type.
    # ========================================================

    @classmethod
    def _select_entry_from_filing(
        cls,
        facts: dict,
        field_name: str,
        filing: dict,
    ) -> Optional[dict]:

        candidates = []

        for entry in (
            cls._iter_fact_entries(
                facts,
                field_name,
            )
        ):

            if not cls._entry_matches_filing(
                entry,
                filing,
            ):
                continue

            candidates.append(
                entry
            )

        if not candidates:
            return None

        form = (
            filing.get(
                "form"
            )
            or ""
        )

        is_annual = (
            form in cls.ANNUAL_FORMS
        )

        def candidate_key(
            entry: dict,
        ):

            end_date = (
                entry.get(
                    "end",
                    "",
                )
            )

            start_date = (
                entry.get(
                    "start"
                )
            )

            duration = None

            if (
                start_date
                and end_date
            ):

                try:

                    start = date.fromisoformat(
                        start_date[:10]
                    )

                    end = date.fromisoformat(
                        end_date[:10]
                    )

                    duration = (
                        end - start
                    ).days + 1

                except ValueError:

                    duration = None

            # ------------------------------------------------
            # Prefer period shape appropriate for filing type.
            # ------------------------------------------------

            duration_match = 0

            if duration is not None:

                if is_annual:

                    if (
                        300
                        <= duration
                        <= 380
                    ):

                        duration_match = 2

                    elif (
                        70
                        <= duration
                        <= 120
                    ):

                        duration_match = 1

                else:

                    if (
                        70
                        <= duration
                        <= 120
                    ):

                        duration_match = 2

                    elif (
                        300
                        <= duration
                        <= 380
                    ):

                        duration_match = 1

            return (
                end_date,
                duration_match,
                entry.get(
                    "filed",
                    "",
                ),
            )

        return max(
            candidates,
            key=candidate_key,
        )

    # ========================================================
    # SNAPSHOT
    # ========================================================

    def get_snapshot(
        self,
        symbol: str,
        as_of_date: Optional[
            str | date | datetime
        ] = None,
    ) -> Optional[
        FundamentalSnapshot
    ]:

        symbol = symbol.upper()

        (
            normalized_as_of,
            as_of_datetime,
        ) = self._normalize_as_of(
            as_of_date
        )

        facts = self.get_company_facts(
            symbol
        )

        if facts is None:
            return None

        # ----------------------------------------------------
        # Find ONE known filing at the cutoff.
        # ----------------------------------------------------

        latest_filing = (
            self._select_latest_available_filing(
                symbol=symbol,
                facts=facts,
                as_of_value=normalized_as_of,
                as_of_datetime=as_of_datetime,
            )
        )

        if latest_filing is None:
            return None

        # ----------------------------------------------------
        # Extract all fields from THAT filing only.
        # ----------------------------------------------------

        values: dict[
            str,
            Optional[float],
        ] = {}

        selected_entries = {}

        for field_name in (
            self.TAG_CANDIDATES
        ):

            entry = (
                self._select_entry_from_filing(
                    facts=facts,
                    field_name=field_name,
                    filing=latest_filing,
                )
            )

            selected_entries[
                field_name
            ] = entry

            if entry is None:

                values[
                    field_name
                ] = None

            else:

                values[
                    field_name
                ] = self._entry_value(
                    entry
                )

        # ----------------------------------------------------
        # Filing metadata
        # ----------------------------------------------------

        filing_date = (
            latest_filing.get(
                "filing_date"
            )
        )

        filing_acceptance_datetime = (
            latest_filing.get(
                "acceptance_datetime"
            )
        )

        filing_accession = (
            latest_filing.get(
                "accession"
            )
        )

        # ----------------------------------------------------
        # Report date:
        #
        # Prefer the latest selected financial period end.
        # Fall back to SEC submission reportDate.
        # ----------------------------------------------------

        selected_end_dates = []

        for entry in (
            selected_entries.values()
        ):

            if entry is None:
                continue

            end = entry.get(
                "end"
            )

            if end is not None:
                selected_end_dates.append(
                    end[:10]
                )

        if selected_end_dates:

            latest_report_date = max(
                selected_end_dates
            )

        else:

            latest_report_date = (
                latest_filing.get(
                    "report_date"
                )
            )

        # ----------------------------------------------------
        # Derived values
        # ----------------------------------------------------

        revenue = values[
            "revenue"
        ]

        net_income = values[
            "net_income"
        ]

        total_assets = values[
            "total_assets"
        ]

        total_liabilities = values[
            "total_liabilities"
        ]

        equity = values[
            "stockholders_equity"
        ]

        cash = values[
            "cash"
        ]

        operating_cash_flow = values[
            "operating_cash_flow"
        ]

        capital_expenditure = values[
            "capital_expenditure"
        ]

        # ----------------------------------------------------
        # FCF
        #
        # SEC normally represents capital expenditure as a
        # positive cash outflow amount.
        # ----------------------------------------------------

        free_cash_flow = None

        if (
            operating_cash_flow is not None
            and capital_expenditure is not None
        ):

            free_cash_flow = (
                operating_cash_flow
                - capital_expenditure
            )

        net_margin = (
            self._safe_divide(
                net_income,
                revenue,
            )
        )

        return_on_equity = (
            self._safe_divide(
                net_income,
                equity,
            )
        )

        debt_to_assets = (
            self._safe_divide(
                total_liabilities,
                total_assets,
            )
        )

        cash_to_assets = (
            self._safe_divide(
                cash,
                total_assets,
            )
        )

        free_cash_flow_margin = (
            self._safe_divide(
                free_cash_flow,
                revenue,
            )
        )

        return FundamentalSnapshot(

            symbol=symbol,

            as_of_date=(
                normalized_as_of
            ),

            report_date=(
                latest_report_date
            ),

            filing_date=(
                filing_date[:10]
                if filing_date
                else None
            ),

            filing_accession=(
                filing_accession
            ),

            filing_acceptance_datetime=(
                filing_acceptance_datetime
            ),

            revenue=revenue,

            net_income=net_income,

            total_assets=total_assets,

            total_liabilities=(
                total_liabilities
            ),

            stockholders_equity=(
                equity
            ),

            cash=cash,

            operating_cash_flow=(
                operating_cash_flow
            ),

            capital_expenditure=(
                capital_expenditure
            ),

            eps=values["eps"],

            net_margin=net_margin,

            return_on_equity=(
                return_on_equity
            ),

            debt_to_assets=(
                debt_to_assets
            ),

            cash_to_assets=(
                cash_to_assets
            ),

            free_cash_flow=(
                free_cash_flow
            ),

            free_cash_flow_margin=(
                free_cash_flow_margin
            ),
        )

    # ========================================================
    # ENTRY VALUE
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

            return float(entry)

        value = entry.get(
            "val"
        )

        if value is None:
            return None

        try:

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None

    # ========================================================
    # CLEAR CACHE
    # ========================================================

    def clear_cache(self) -> None:

        self._facts_cache.clear()

        self._submissions_cache.clear()

        self._submission_file_cache.clear()

        self._filing_metadata_cache.clear()