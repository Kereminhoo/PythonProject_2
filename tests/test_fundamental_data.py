from datetime import date, datetime, timezone

from data.fundamental_data import (
    FundamentalData,
    FundamentalSnapshot,
)


class FakeSettings:
    pass


def make_engine():

    return FundamentalData(
        FakeSettings()
    )


# ============================================================
# CIK
# ============================================================


def test_known_symbol_has_cik():

    engine = make_engine()

    cik = engine.get_cik(
        "AAPL"
    )

    assert cik == "0000320193"


def test_unknown_symbol_has_no_cik():

    engine = make_engine()

    cik = engine.get_cik(
        "NOTAREALSTOCK"
    )

    assert cik is None


# ============================================================
# DATE NORMALIZATION
# ============================================================


def test_normalize_date_from_string():

    engine = make_engine()

    result = engine._normalize_date(
        "2025-01-15T12:00:00"
    )

    assert result == "2025-01-15"


def test_normalize_date_from_date():

    engine = make_engine()

    result = engine._normalize_date(
        date(2025, 1, 15)
    )

    assert result == "2025-01-15"


# ============================================================
# LATEST VALUE
# ============================================================


def test_extract_latest_value():

    fact = {

        "units": {

            "USD": [

                {
                    "val": 100,
                    "end": "2024-12-31",
                    "filed": "2025-02-01",
                },

                {
                    "val": 200,
                    "end": "2025-03-31",
                    "filed": "2025-05-01",
                },
            ]
        }
    }

    value, report_date, filing_date = (
        FundamentalData._extract_latest_value(
            fact
        )
    )

    assert value == 200
    assert report_date == "2025-03-31"
    assert filing_date == "2025-05-01"


# ============================================================
# AS-OF DATE
# ============================================================


def test_as_of_date_blocks_future_filing():

    fact = {

        "units": {

            "USD": [

                {
                    "val": 100,
                    "end": "2024-12-31",
                    "filed": "2025-02-01",
                },

                {
                    "val": 200,
                    "end": "2025-03-31",
                    "filed": "2025-05-01",
                },
            ]
        }
    }

    value, report_date, filing_date = (
        FundamentalData._extract_latest_value(
            fact,
            as_of_date="2025-03-01",
        )
    )

    assert value == 100
    assert report_date == "2024-12-31"
    assert filing_date == "2025-02-01"


def test_as_of_date_returns_none_when_no_known_data():

    fact = {

        "units": {

            "USD": [

                {
                    "val": 200,
                    "end": "2025-03-31",
                    "filed": "2025-05-01",
                },
            ]
        }
    }

    value, report_date, filing_date = (
        FundamentalData._extract_latest_value(
            fact,
            as_of_date="2025-04-01",
        )
    )

    assert value is None
    assert report_date is None
    assert filing_date is None


# ============================================================
# EMPTY DATA
# ============================================================


def test_empty_fact_returns_none():

    value, report_date, filing_date = (
        FundamentalData._extract_latest_value(
            {}
        )
    )

    assert value is None
    assert report_date is None
    assert filing_date is None


# ============================================================
# DERIVED RATIOS
# ============================================================


def test_safe_divide():

    assert (
        FundamentalData._safe_divide(
            20,
            100,
        )
        == 0.20
    )


def test_safe_divide_zero_denominator():

    assert (
        FundamentalData._safe_divide(
            20,
            0,
        )
        is None
    )


def test_snapshot_derived_metrics():

    snapshot = FundamentalSnapshot(

        symbol="AAPL",

        as_of_date="2025-05-15",

        report_date="2025-03-31",

        filing_date="2025-05-01",

        revenue=1000.0,

        net_income=200.0,

        total_assets=5000.0,

        total_liabilities=3000.0,

        stockholders_equity=2000.0,

        cash=1000.0,

        operating_cash_flow=250.0,

        capital_expenditure=100.0,

        eps=1.50,

        net_margin=0.20,

        return_on_equity=0.10,

        debt_to_assets=0.60,

        cash_to_assets=0.20,

        free_cash_flow=150.0,

        free_cash_flow_margin=0.15,
    )

    assert snapshot.symbol == "AAPL"

    assert snapshot.revenue == 1000.0

    assert snapshot.net_income == 200.0

    assert snapshot.eps == 1.50

    assert snapshot.free_cash_flow == 150.0

    assert snapshot.net_margin == 0.20


# ============================================================
# TAG RESOLUTION
# ============================================================


def test_find_fact():

    facts = {

        "facts": {

            "us-gaap": {

                "Assets": {

                    "units": {

                        "USD": []
                    }
                }
            }
        }
    }

    fact = FundamentalData._find_fact(
        facts,
        ["Assets"],
    )

    assert fact is not None


# ============================================================
# SNAPSHOT OBJECT
# ============================================================


def test_snapshot_dataclass():

    snapshot = FundamentalSnapshot(

        symbol="AAPL",

        as_of_date="2025-03-01",

        report_date="2024-12-31",

        filing_date="2025-02-01",

        revenue=1000.0,

        net_income=200.0,

        total_assets=5000.0,

        total_liabilities=3000.0,

        stockholders_equity=2000.0,

        cash=1000.0,

        operating_cash_flow=250.0,

        capital_expenditure=100.0,

        eps=1.50,

        net_margin=0.20,

        return_on_equity=0.10,

        debt_to_assets=0.60,

        cash_to_assets=0.20,

        free_cash_flow=150.0,

        free_cash_flow_margin=0.15,
    )

    assert snapshot.symbol == "AAPL"

    assert snapshot.as_of_date == "2025-03-01"

    assert snapshot.filing_date == "2025-02-01"

    assert snapshot.return_on_equity == 0.10


# ============================================================
# INTRADAY POINT-IN-TIME
# ============================================================


def test_entry_is_available_only_after_acceptance_datetime():

    engine = make_engine()

    engine.get_filing_metadata = (
        lambda **kwargs: {
            "acceptance_datetime": (
                "2025-05-15T14:00:00Z"
            )
        }
    )

    entry = {

        "filed": "2025-05-15",

        "accn": "0000000001",
    }

    before_filing = datetime(
        2025,
        5,
        15,
        13,
        59,
        tzinfo=timezone.utc,
    )

    after_filing = datetime(
        2025,
        5,
        15,
        14,
        1,
        tzinfo=timezone.utc,
    )

    assert (
        engine._entry_is_available(
            symbol="AAPL",
            entry=entry,
            as_of_value=before_filing.isoformat(),
            as_of_datetime=before_filing,
        )
        is False
    )

    assert (
        engine._entry_is_available(
            symbol="AAPL",
            entry=entry,
            as_of_value=after_filing.isoformat(),
            as_of_datetime=after_filing,
        )
        is True
    )


def test_same_day_filing_without_acceptance_time_is_blocked_intraday():

    engine = make_engine()

    engine.get_filing_metadata = (
        lambda **kwargs: {
            "acceptance_datetime": None
        }
    )

    entry = {

        "filed": "2025-05-15",

        "accn": "0000000002",
    }

    same_day_cutoff = datetime(
        2025,
        5,
        15,
        16,
        0,
        tzinfo=timezone.utc,
    )

    previous_day_cutoff = datetime(
        2025,
        5,
        14,
        16,
        0,
        tzinfo=timezone.utc,
    )

    assert (
        engine._entry_is_available(
            symbol="AAPL",
            entry=entry,
            as_of_value=same_day_cutoff.isoformat(),
            as_of_datetime=same_day_cutoff,
        )
        is False
    )

    assert (
        engine._entry_is_available(
            symbol="AAPL",
            entry=entry,
            as_of_value=previous_day_cutoff.isoformat(),
            as_of_datetime=previous_day_cutoff,
        )
        is False
    )


def test_latest_available_filing_uses_cutoff_time():

    engine = make_engine()

    facts = {

        "facts": {

            "us-gaap": {

                "RevenueFromContractWithCustomerExcludingAssessedTax": {

                    "units": {

                        "USD": [

                            {
                                "val": 100.0,
                                "start": "2025-01-01",
                                "end": "2025-03-31",
                                "filed": "2025-05-15",
                                "accn": "ACC-A",
                            },

                            {
                                "val": 200.0,
                                "start": "2025-01-01",
                                "end": "2025-03-31",
                                "filed": "2025-05-15",
                                "accn": "ACC-B",
                            },
                        ]
                    }
                }
            }
        }
    }

    metadata = {

        "ACC-A": {
            "acceptance_datetime": (
                "2025-05-15T11:00:00Z"
            ),
            "report_date": "2025-03-31",
            "form": "10-Q",
        },

        "ACC-B": {
            "acceptance_datetime": (
                "2025-05-15T16:00:00Z"
            ),
            "report_date": "2025-03-31",
            "form": "10-Q",
        },
    }

    engine.get_filing_metadata = (
        lambda symbol, accession, filing_date=None:
            metadata[accession]
    )

    cutoff = datetime(
        2025,
        5,
        15,
        14,
        0,
        tzinfo=timezone.utc,
    )

    selected = (
        engine._select_latest_available_filing(
            symbol="AAPL",
            facts=facts,
            as_of_value=cutoff.isoformat(),
            as_of_datetime=cutoff,
        )
    )

    assert selected is not None

    assert (
        selected["accession"]
        == "ACC-A"
    )

    assert (
        selected["acceptance_datetime"]
        == "2025-05-15T11:00:00Z"
    )


def test_snapshot_does_not_mix_different_filings():

    facts = {

        "facts": {

            "us-gaap": {

                "RevenueFromContractWithCustomerExcludingAssessedTax": {

                    "units": {

                        "USD": [

                            {
                                "val": 100.0,
                                "start": "2025-01-01",
                                "end": "2025-03-31",
                                "filed": "2025-05-01",
                                "accn": "ACC-A",
                            },

                            {
                                "val": 200.0,
                                "start": "2025-01-01",
                                "end": "2025-03-31",
                                "filed": "2025-05-01",
                                "accn": "ACC-B",
                            },
                        ]
                    }
                },

                "NetIncomeLoss": {

                    "units": {

                        "USD": [

                            {
                                "val": 10.0,
                                "start": "2025-01-01",
                                "end": "2025-03-31",
                                "filed": "2025-05-01",
                                "accn": "ACC-A",
                            },

                            {
                                "val": 20.0,
                                "start": "2025-01-01",
                                "end": "2025-03-31",
                                "filed": "2025-05-01",
                                "accn": "ACC-B",
                            },
                        ]
                    }
                },

                "Assets": {

                    "units": {

                        "USD": [

                            {
                                "val": 1000.0,
                                "end": "2025-03-31",
                                "filed": "2025-05-01",
                                "accn": "ACC-A",
                            },
                        ]
                    }
                },
            }
        }
    }

    metadata = {

        "ACC-A": {
            "acceptance_datetime": (
                "2025-05-01T10:00:00Z"
            ),
            "report_date": "2025-03-31",
            "form": "10-Q",
        },

        "ACC-B": {
            "acceptance_datetime": (
                "2025-05-01T15:00:00Z"
            ),
            "report_date": "2025-03-31",
            "form": "10-Q",
        },
    }

    engine = make_engine()

    engine.get_company_facts = (
        lambda symbol: facts
    )

    engine.get_filing_metadata = (
        lambda symbol, accession, filing_date=None:
            metadata[accession]
    )

    cutoff = datetime(
        2025,
        5,
        1,
        16,
        0,
        tzinfo=timezone.utc,
    )

    snapshot = engine.get_snapshot(
        "AAPL",
        cutoff,
    )

    assert snapshot is not None

    assert snapshot.revenue == 200.0

    assert snapshot.net_income == 20.0

    # Assets only exist in ACC-A.
    # They must NOT leak into the ACC-B snapshot.
    assert snapshot.total_assets is None

    assert (
        snapshot.filing_accession
        == "ACC-B"
    )

    assert (
        snapshot.filing_acceptance_datetime
        == "2025-05-01T15:00:00Z"
    )

def test_normalize_as_of_date_only_has_no_intraday_cutoff():

    engine = make_engine()

    normalized, as_of_datetime = (
        engine._normalize_as_of(
            "2025-01-15"
        )
    )

    assert normalized == "2025-01-15"

    assert as_of_datetime is None


def test_normalize_as_of_datetime_preserves_time():

    engine = make_engine()

    normalized, as_of_datetime = (
        engine._normalize_as_of(
            "2025-01-15T14:30:00Z"
        )
    )

    assert (
        normalized
        == "2025-01-15T14:30:00+00:00"
    )

    assert as_of_datetime is not None

    assert (
        as_of_datetime.hour
        == 14
    )

    assert (
        as_of_datetime.minute
        == 30
    )