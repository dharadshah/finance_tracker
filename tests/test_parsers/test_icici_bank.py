"""
Tests for the ICICI Bank CSV parser.
Uses the real statement file from tests/ directory.
"""

import pytest
from pathlib import Path
from decimal import Decimal

from finance_tracker.parsers.icici_bank import ICICIBankParser
from finance_tracker.parsers.base import ParseResult

SAMPLE_FILE = Path(__file__).parent.parent / "EStatement_M3_511939011_005201526760.CSV"


@pytest.fixture(scope="module")
def result() -> ParseResult:
    parser = ICICIBankParser()
    return parser.process(SAMPLE_FILE)


def test_no_errors(result):
    assert not result.has_errors, f"Parser errors: {result.errors}"


def test_institution(result):
    assert result.institution == "ICICI Bank"


def test_account_number_masked(result):
    assert result.account_number_masked is not None
    assert "XXXX" in result.account_number_masked


def test_account_holder_name_scrubbed(result):
    """Personal name must never be stored."""
    assert result.account_holder_name is None


def test_statement_period_parsed(result):
    from datetime import date
    assert result.statement_period_start == date(2026, 3, 1)
    assert result.statement_period_end == date(2026, 3, 31)


def test_transactions_found(result):
    assert result.transaction_count > 0


def test_no_bf_row(result):
    """B/F carry-forward row must be excluded."""
    for txn in result.transactions:
        assert txn.raw_description.strip() != "B/F"


def test_all_amounts_positive(result):
    for txn in result.transactions:
        assert txn.amount > 0, f"Non-positive amount: {txn}"


def test_dr_cr_values_valid(result):
    for txn in result.transactions:
        assert txn.dr_cr in ("DR", "CR"), f"Invalid dr_cr: {txn.dr_cr}"


def test_descriptions_cleaned(result):
    """Cleaned descriptions must not contain raw UPI transaction hashes."""
    import re
    hash_pattern = re.compile(r"[A-F0-9]{20,}", re.IGNORECASE)
    for txn in result.transactions:
        assert not hash_pattern.search(txn.description), (
            f"Hash found in description: {txn.description!r}"
        )


def test_upi_description_format(result):
    """UPI transactions should produce readable descriptions."""
    upi_txns = [t for t in result.transactions if t.raw_description.startswith("UPI/")]
    assert len(upi_txns) > 0
    for txn in upi_txns:
        assert txn.description.startswith("UPI /"), (
            f"Unexpected UPI description: {txn.description!r}"
        )


def test_source_file_set(result):
    for txn in result.transactions:
        assert txn.source_file is not None
        assert "/" not in txn.source_file  # must be filename only, not full path


def test_known_transaction(result):
    """Spot-check a specific transaction we can see in the file."""
    # Line 53: Swiggy on 02-03-2026, withdrawal of 105
    swiggy = [
        t for t in result.transactions
        if "Swiggy" in t.description and t.amount == Decimal("105")
    ]
    assert len(swiggy) >= 1
    assert swiggy[0].dr_cr == "DR"


def test_large_credit_imps(result):
    """02-03-2026: IMPS credit of 100000 from Axis Bank."""
    imps = [
        t for t in result.transactions
        if t.amount == Decimal("100000") and t.dr_cr == "CR"
    ]
    assert len(imps) >= 1
    assert "IMPS" in imps[0].description or "Dharadhava" in imps[0].description


def test_registry_lookup():
    from finance_tracker.parsers.registry import get_parser
    parser = get_parser("icici_bank")
    assert isinstance(parser, ICICIBankParser)


def test_registry_unknown_key():
    from finance_tracker.parsers.registry import get_parser
    with pytest.raises(KeyError, match="No parser registered"):
        get_parser("nonexistent_bank")
