import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from finance_tracker.parsers.base import BaseStatementParser, ParseResult, ParsedTransaction

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%d/%m/%Y"


class AxisCreditCardParser(BaseStatementParser):
    """
    Parser for Axis Bank Credit Card PDF statements.
    Extracts transactions from the Account Summary table on page 1.
    """

    INSTITUTION = "Axis Credit Card"

    def parse(self, file_path: Path) -> ParseResult:
        result = ParseResult(institution=self.INSTITUTION)

        try:
            with pdfplumber.open(str(file_path)) as pdf:
                page = pdf.pages[0]
                tables = page.extract_tables()
        except Exception as e:
            result.errors.append(f"Could not read PDF: {e}")
            return result

        # Find the account summary table — has DATE column
        txn_table = None
        for table in tables:
            for row in table:
                if row and any(cell == "DATE" for cell in row if cell):
                    txn_table = table
                    break
            if txn_table:
                break

        if not txn_table:
            result.errors.append("Could not find transaction table in PDF")
            return result

        # Extract metadata from first row
        self._extract_metadata(txn_table, result)

        # Parse transaction rows
        dates = []
        in_transactions = False
        for row in txn_table:
            if not row:
                continue

            # Skip header row
            if any(cell == "DATE" for cell in row if cell):
                in_transactions = True
                continue

            if not in_transactions:
                continue

            # Stop at end of statement
            first_cell = row[0] or ""
            if "End of Statement" in first_cell:
                break

            txn = self._parse_row(row, file_path.name)
            if txn:
                result.transactions.append(txn)
                dates.append(txn.txn_date)

        if dates:
            result.statement_period_start = min(dates)
            result.statement_period_end = max(dates)

        logger.info(
            "Axis Credit Card parser: %d transactions from %s",
            result.transaction_count,
            file_path.name,
        )
        return result

    def _extract_metadata(self, table: list, result: ParseResult) -> None:
        for row in table:
            if not row:
                continue
            for cell in row:
                if cell and re.search(r'\d{6}\*+\d{4}', cell):
                    masked = re.search(r'(\d{6}\*+\d{4})', cell)
                    if masked:
                        result.account_number_masked = masked.group(1)
                    break

    def _parse_row(self, row: list, filename: str) -> ParsedTransaction | None:
        # Row format: [date, None, description, None, ..., merchant_category, amount]
        raw_date = row[0]
        if not raw_date or not raw_date.strip():
            return None

        # Parse date
        try:
            txn_date = datetime.strptime(raw_date.strip(), _DATE_FORMAT).date()
        except ValueError:
            return None

        # Description is in column 2
        particulars = row[2] or ""
        if not particulars.strip():
            return None

        # Amount is in last column
        amount_str = row[-1] or ""
        if not amount_str.strip():
            return None

        # Determine DR/CR and parse amount
        amount_str = amount_str.strip()
        if amount_str.endswith(" Cr"):
            dr_cr = "CR"
            amount_str = amount_str[:-3].strip()
        elif amount_str.endswith(" Dr"):
            dr_cr = "DR"
            amount_str = amount_str[:-3].strip()
        else:
            dr_cr = "DR"  # default to debit

        try:
            amount = Decimal(amount_str.replace(",", "").strip())
        except InvalidOperation:
            return None

        if amount <= 0:
            return None

        return ParsedTransaction(
            txn_date=txn_date,
            amount=amount,
            dr_cr=dr_cr,
            description="",
            raw_description=particulars.strip(),
            reference_number=None,
            mode="Credit Card",
            source_file=filename,
        )

    def _clean_description(self, raw: str) -> str:
        desc = raw.strip()

        # BBPS payment received
        if "BBPS" in desc.upper() and "RECEIVED" in desc.upper():
            return "Credit Card Payment"

        # Remove trailing city and country
        desc = re.sub(r',\s*[A-Z\s]+$', '', desc)

        return desc.strip().title()