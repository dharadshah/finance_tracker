import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from finance_tracker.parsers.base import BaseStatementParser, ParseResult, ParsedTransaction

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%d/%m/%Y"


class YesBankParser(BaseStatementParser):
    """
    Parser for Yes Bank PDF statements.
    Transactions are in a table on page 3 with columns:
    Transaction Date, Value Date, Description, Cheque/Reference No.,
    Withdrawals, Deposits, Running Balance
    """

    INSTITUTION = "Yes Bank"

    def parse(self, file_path: Path) -> ParseResult:
        result = ParseResult(institution=self.INSTITUTION)

        try:
            with pdfplumber.open(str(file_path)) as pdf:
                # Extract metadata from page 1
                self._extract_metadata(pdf.pages[0], result)

                # Transactions are on page 3 (index 2)
                # But iterate all pages in case of multi-page statements
                last_balance = None
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table:
                            continue
                        # Find transaction table by header
                        for i, row in enumerate(table):
                            if row and any(
                                cell and "Transaction" in cell and "Date" in cell
                                for cell in row if cell
                            ):
                                # Parse from next row
                                for txn_row in table[i + 1:]:
                                    txn = self._parse_row(txn_row, file_path.name)
                                    if txn:
                                        result.transactions.append(txn)
                                        if txn.balance is not None:
                                            last_balance = txn.balance
                                break

                result.closing_balance = last_balance

        except Exception as e:
            result.errors.append(f"Could not read PDF: {e}")
            return result

        # Set period from transactions
        if result.transactions:
            dates = [t.txn_date for t in result.transactions]
            result.statement_period_start = min(dates)
            result.statement_period_end = max(dates)

        logger.info(
            "Yes Bank parser: %d transactions from %s",
            result.transaction_count,
            file_path.name,
        )
        return result

    def _extract_metadata(self, page, result: ParseResult) -> None:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row:
                    continue
                for cell in row:
                    if cell and re.search(r'\d{15,}', cell):
                        match = re.search(r'(\d{15,})', cell)
                        if match:
                            full = match.group(1)
                            result.account_number_masked = f"XXXXXX{full[-4:]}"

    def _parse_row(self, row: list, filename: str) -> ParsedTransaction | None:
        if not row or len(row) < 6:
            return None

        raw_date = row[0]
        if not raw_date or not raw_date.strip():
            return None

        # Clean up date — sometimes has newlines
        raw_date = raw_date.strip().split('\n')[0].strip()

        # Parse date
        try:
            txn_date = datetime.strptime(raw_date, _DATE_FORMAT).date()
        except ValueError:
            return None

        # Description — may have newlines
        particulars = (row[2] or "").replace('\n', ' ').strip()
        if not particulars or particulars == "B/F ...":
            return None

        # Reference number
        reference = (row[3] or "").strip() or None

        # Withdrawals and deposits
        withdrawal_str = (row[4] or "").strip()
        deposit_str = (row[5] or "").strip()
        balance_str = (row[6] or "").strip() if len(row) > 6 else ""

        withdrawal = self._to_decimal(withdrawal_str)
        deposit = self._to_decimal(deposit_str)

        if deposit > 0 and withdrawal == 0:
            amount = deposit
            dr_cr = "CR"
        elif withdrawal > 0 and deposit == 0:
            amount = withdrawal
            dr_cr = "DR"
        else:
            return None

        # Parse balance
        try:
            balance = Decimal(balance_str.replace(",", "").strip()) if balance_str else None
        except InvalidOperation:
            balance = None

        return ParsedTransaction(
            txn_date=txn_date,
            amount=amount,
            dr_cr=dr_cr,
            description="",
            raw_description=particulars,
            reference_number=reference if reference else None,
            mode=None,
            balance=balance,
            source_file=filename,
        )