import csv
import re
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from finance_tracker.parsers.base import BaseStatementParser, ParseResult, ParsedTransaction

logger = logging.getLogger(__name__)

# The exact header row that marks the start of transactions in ICICI CSV
_TXN_HEADER = "DATE,MODE,PARTICULARS,DEPOSITS,WITHDRAWALS,BALANCE"

# Date format used by ICICI: 01-03-2026
_DATE_FORMAT = "%d-%m-%Y"


class ICICIBankParser(BaseStatementParser):
    """
    Parser for ICICI Bank savings account CSV statements.

    Statement structure:
    - Lines 1–N:   Personal info, account summary, FD summary (skip)
    - Marker row:  DATE,MODE,PARTICULARS,DEPOSITS,WITHDRAWALS,BALANCE
    - Data rows:   Transactions (may include B/F carry-forward row — skipped)
    - End marker:  Blank line or non-transaction section header

    One parser instance per file. A second ICICI account gets the same
    parser class — differentiated by the account_number_masked in ParseResult.
    """

    INSTITUTION = "ICICI Bank"

    def parse(self, file_path: Path) -> ParseResult:
        result = ParseResult(institution=self.INSTITUTION)

        try:
            raw_lines = file_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except Exception as e:
            result.errors.append(f"Could not read file: {e}")
            return result

        # Extract account number and statement period from headers
        self._extract_metadata(raw_lines, result)

        # Find the transaction section
        txn_start = self._find_transaction_start(raw_lines)
        if txn_start is None:
            result.errors.append(
                "Could not find transaction header row. "
                f"Expected: '{_TXN_HEADER}'"
            )
            return result

        # Parse transactions
        self._parse_transactions(raw_lines[txn_start + 1:], result, file_path.name)

        logger.info(
            "ICICI parser: %d transactions from %s (account %s)",
            result.transaction_count,
            file_path.name,
            result.account_number_masked,
        )
        return result

    def _extract_metadata(self, lines: list[str], result: ParseResult) -> None:
        for line in lines:
            # Account number (masked): Savings A/c XXXXXXXX6760
            acct_match = re.search(r"Savings A/c\s+(X+\d+)", line)
            if acct_match:
                result.account_number_masked = acct_match.group(1)

            # Statement period: March 01 2026 - March 31 2026
            period_match = re.search(
                r"for the period\s*[-–]?\s*(\w+ \d{1,2}\s+\d{4})\s*[-–]\s*(\w+ \d{1,2}\s+\d{4})",
                line,
            )
            if period_match:
                try:
                    result.statement_period_start = datetime.strptime(
                        period_match.group(1).strip(), "%B %d  %Y"
                    ).date()
                    result.statement_period_end = datetime.strptime(
                        period_match.group(2).strip(), "%B %d  %Y"
                    ).date()
                except ValueError:
                    result.warnings.append(f"Could not parse statement period: {line.strip()}")

    def _find_transaction_start(self, lines: list[str]) -> int | None:
        for i, line in enumerate(lines):
            if line.strip().startswith("DATE,MODE,PARTICULARS"):
                return i
        return None

    def _parse_transactions(self, lines, result, filename):
        last_balance = None
        for line in lines:
            line = line.strip()
            if not line:
                break
            if line.startswith("Statement of Linked") or line.startswith("FIXED DEPOSIT"):
                break
            if ",B/F," in line:
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
        # Use csv.reader to handle commas inside quoted fields correctly
        parts = next(csv.reader([line]))

        if len(parts) < 6:
            return None

        raw_date, mode, particulars, deposits, withdrawals, balance = (
            parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        )

        # Parse date
        try:
            txn_date = datetime.strptime(raw_date.strip(), _DATE_FORMAT).date()
        except ValueError:
            return None

        # Parse amounts
        deposit_amt = self._to_decimal(deposits)
        withdrawal_amt = self._to_decimal(withdrawals)

        # Determine direction
        if deposit_amt > 0 and withdrawal_amt == 0:
            amount = deposit_amt
            dr_cr = "CR"
        elif withdrawal_amt > 0 and deposit_amt == 0:
            amount = withdrawal_amt
            dr_cr = "DR"
        elif deposit_amt > 0 and withdrawal_amt > 0:
            # Edge case: both non-zero — take the larger as the direction
            if deposit_amt >= withdrawal_amt:
                amount = deposit_amt
                dr_cr = "CR"
            else:
                amount = withdrawal_amt
                dr_cr = "DR"
        else:
            # Both zero — skip (informational row)
            return None

        # Extract reference number from UPI/IMPS strings
        ref_match = re.search(r"/(\d{12,})/", particulars)
        reference = ref_match.group(1) if ref_match else None

        # Clean mode
        mode_clean = mode.strip() if mode.strip() else None

        # Parse balance (may be negative for overdraft)
        try:
            bal = Decimal(balance.replace(",", "").strip())
        except InvalidOperation:
            bal = None

        return ParsedTransaction(
            txn_date=txn_date,
            amount=amount,
            dr_cr=dr_cr,
            description="",          # filled by base.process() after cleaning
            raw_description=particulars.strip(),
            reference_number=reference,
            mode=mode_clean,
            balance=bal,
            source_file=filename,
        )
