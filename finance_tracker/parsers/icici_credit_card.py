import csv
import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from finance_tracker.parsers.base import BaseStatementParser, ParseResult, ParsedTransaction

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%d/%m/%Y"


class ICICICreditCardParser(BaseStatementParser):
    """
    Parser for ICICI Bank Credit Card CSV statements.

    Statement structure:
    - Lines 1-N:  Account info, address (skip)
    - Blank lines (skip)
    - "Transaction Details:" marker (skip)
    - Header row: Date,Sr.No.,Transaction Details,...,Amount(in Rs),BillingAmountSign
    - Card number row (skip)
    - Data rows: Transactions
    """

    INSTITUTION = "ICICI Credit Card"

    def parse(self, file_path: Path) -> ParseResult:
        result = ParseResult(institution=self.INSTITUTION)

        try:
            raw_lines = file_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except Exception as e:
            result.errors.append(f"Could not read file: {e}")
            return result

        self._extract_metadata(raw_lines, result)

        txn_start = self._find_transaction_start(raw_lines)
        if txn_start is None:
            result.errors.append("Could not find transaction header row")
            return result

        self._parse_transactions(raw_lines[txn_start + 1:], result, file_path.name)

        logger.info(
            "ICICI Credit Card parser: %d transactions from %s",
            result.transaction_count,
            file_path.name,
        )
        return result

    def _extract_metadata(self, lines: list[str], result: ParseResult) -> None:
        for line in lines:
            # Account number
            acct_match = re.search(r'Accountno.*?(\d{10,})', line)
            if acct_match:
                full = acct_match.group(1)
                result.account_number_masked = f"XXXXXX{full[-4:]}"

    def _find_transaction_start(self, lines: list[str]) -> int | None:
        for i, line in enumerate(lines):
            if "Date" in line and "Transaction Details" in line and "Amount" in line:
                return i
        return None

    def _parse_transactions(
        self, lines: list[str], result: ParseResult, filename: str
    ) -> None:
        dates = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                txn = self._parse_row(line, filename)
                if txn is not None:
                    result.transactions.append(txn)
                    dates.append(txn.txn_date)
            except Exception as e:
                result.warnings.append(f"Skipped row: {line[:80]!r} — {e}")

        if dates:
            result.statement_period_start = min(dates)
            result.statement_period_end = max(dates)

    def _parse_row(self, line: str, filename: str) -> ParsedTransaction | None:
        parts = next(csv.reader([line]))

        if len(parts) < 6:
            return None

        raw_date = parts[0].strip().strip('"')
        sr_no = parts[1].strip().strip('"')
        particulars = parts[2].strip().strip('"')
        amount_str = parts[5].strip().strip('"')
        billing_sign = parts[6].strip().strip('"') if len(parts) > 6 else ""

        # Skip card number rows and header rows
        if not raw_date or len(raw_date) < 8:
            return None

        # Parse date
        try:
            txn_date = datetime.strptime(raw_date, _DATE_FORMAT).date()
        except ValueError:
            return None

        # Parse amount
        try:
            amount = Decimal(amount_str.replace(",", "").strip())
        except InvalidOperation:
            return None

        if amount <= 0:
            return None

        # CR = payment received (credit), empty = expense (debit)
        dr_cr = "CR" if billing_sign.upper() == "CR" else "DR"

        return ParsedTransaction(
            txn_date=txn_date,
            amount=amount,
            dr_cr=dr_cr,
            description="",
            raw_description=particulars,
            reference_number=sr_no if sr_no else None,
            mode="Credit Card",
            source_file=filename,
        )

    def _clean_description(self, raw: str) -> str:
        """Clean credit card merchant descriptions."""
        import re
        desc = raw.strip()

        # BBPS payment
        if "BBPS" in desc.upper():
            return "Credit Card Payment"

        # UPI payment
        if desc.upper().startswith("UPI"):
            return f"UPI / {desc[4:].strip().title()}"

        # Clean up merchant name — remove city, country codes at end
        # e.g. "UBER INDIA SYSTE PVT LTD NOIDA IN" -> "Uber India"
        # Remove trailing IN, US, UK etc country codes
        desc = re.sub(r'\s+[A-Z]{2}\s*\*?\s*$', '', desc)
        # Remove trailing city names in caps
        desc = re.sub(r'\s+[A-Z\s]{4,}$', '', desc)

        return desc.strip().title()