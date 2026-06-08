import csv
import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from finance_tracker.parsers.base import BaseStatementParser, ParseResult, ParsedTransaction

logger = logging.getLogger(__name__)

_TXN_HEADER = "Tran Date,CHQNO,PARTICULARS,DR,CR,BAL,SOL"
_DATE_FORMAT = "%d-%m-%Y"


class AxisBankParser(BaseStatementParser):
    """
    Parser for Axis Bank savings account CSV statements.

    Statement structure:
    - Lines 1–N:  Personal info, address, account summary (skip)
    - Marker row: Tran Date,CHQNO,PARTICULARS,DR,CR,BAL,SOL
    - Data rows:  Transactions
    """

    INSTITUTION = "Axis Bank"

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
            result.errors.append(
                f"Could not find transaction header row. Expected: '{_TXN_HEADER}'"
            )
            return result

        self._parse_transactions(raw_lines[txn_start + 1:], result, file_path.name)

        logger.info(
            "Axis Bank parser: %d transactions from %s (account %s)",
            result.transaction_count,
            file_path.name,
            result.account_number_masked,
        )
        return result

    def _extract_metadata(self, lines: list[str], result: ParseResult) -> None:
        for line in lines:
            # Account number: "Statement of Account No - 922010036452224 for the period..."
            acct_match = re.search(r"Account No\s*-\s*(\d+)", line)
            if acct_match:
                full = acct_match.group(1)
                result.account_number_masked = f"XXXXXX{full[-4:]}"

            # Period: "From : 06-12-2025  To : 06-06-2026"
            period_match = re.search(
                r"From\s*:\s*(\d{2}-\d{2}-\d{4})\s+To\s*:\s*(\d{2}-\d{2}-\d{4})",
                line,
            )
            if period_match:
                try:
                    result.statement_period_start = datetime.strptime(
                        period_match.group(1), _DATE_FORMAT
                    ).date()
                    result.statement_period_end = datetime.strptime(
                        period_match.group(2), _DATE_FORMAT
                    ).date()
                except ValueError:
                    result.warnings.append(f"Could not parse period: {line.strip()}")

    def _find_transaction_start(self, lines: list[str]) -> int | None:
        for i, line in enumerate(lines):
            if line.strip().startswith("Tran Date,CHQNO,PARTICULARS"):
                return i
        return None

    def _parse_transactions(self, lines, result, filename):
        last_balance = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                txn = self._parse_row(line, filename)
                if txn is not None:
                    result.transactions.append(txn)
                    if txn.balance is not None:
                        last_balance = txn.balance
            except Exception as e:
                result.warnings.append(f"Skipped row: {line[:80]!r} — {e}")
        result.closing_balance = last_balance

    def _parse_row(self, line: str, filename: str) -> ParsedTransaction | None:
        parts = next(csv.reader([line]))

        if len(parts) < 5:
            return None

        raw_date = parts[0].strip()
        particulars = parts[2].strip()
        dr = parts[3].strip()
        cr = parts[4].strip()
        bal = parts[5].strip() if len(parts) > 5 else ""

        # Parse date
        try:
            txn_date = datetime.strptime(raw_date, _DATE_FORMAT).date()
        except ValueError:
            return None

        # Parse amounts
        dr_amt = self._to_decimal(dr)
        cr_amt = self._to_decimal(cr)

        if cr_amt > 0 and dr_amt == 0:
            amount = cr_amt
            dr_cr = "DR"
        elif dr_amt > 0 and cr_amt == 0:
            amount = dr_amt
            dr_cr = "CR"
        else:
            return None

        # Extract reference number
        ref_match = re.search(r"/(\d{12,})/", particulars)
        reference = ref_match.group(1) if ref_match else None

        # Parse balance
        try:
            balance = Decimal(bal.replace(",", "").strip()) if bal else None
        except InvalidOperation:
            balance = None

        return ParsedTransaction(
            txn_date=txn_date,
            amount=amount,
            dr_cr=dr_cr,
            description="",
            raw_description=particulars,
            reference_number=reference,
            mode=None,
            balance=balance,
            source_file=filename,
        )