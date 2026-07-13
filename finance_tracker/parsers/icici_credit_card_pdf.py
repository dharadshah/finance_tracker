import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from finance_tracker.parsers.base import BaseStatementParser, ParseResult, ParsedTransaction

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%d-%b-%y"


class ICICICreditCardPDFParser(BaseStatementParser):
    """
    Parser for ICICI Bank Credit Card PDF e-statements.
    Handles multi-year statements which may have multiple
    'TRANSACTION DETAILS' tables for different card numbers
    (e.g. old card replaced with new card number).

    Negative amount = payment received (credit)
    Positive amount = purchase (debit)
    """

    INSTITUTION = "ICICI Credit Card"

    def parse(self, file_path: Path) -> ParseResult:
        result = ParseResult(institution=self.INSTITUTION)

        try:
            with pdfplumber.open(str(file_path)) as pdf:
                self._extract_metadata(pdf.pages[0], result)

                dates = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table:
                            continue
                        # Identify transaction tables by header
                        header = table[0] if table else []
                        if not any(
                            cell and "Ref. Number" in cell
                            for cell in header if cell
                        ):
                            continue

                        for row in table[1:]:
                            txn = self._parse_row(row, file_path.name)
                            if txn:
                                result.transactions.append(txn)
                                dates.append(txn.txn_date)

                if dates:
                    result.statement_period_start = min(dates)
                    result.statement_period_end = max(dates)

        except Exception as e:
            result.errors.append(f"Could not read PDF: {e}")
            return result

        logger.info(
            "ICICI Credit Card PDF parser: %d transactions from %s",
            result.transaction_count,
            file_path.name,
        )
        return result

    def _extract_metadata(self, page, result: ParseResult) -> None:
        text = page.extract_text() or ""
        match = re.search(r'(\d{4}\s*X+\s*X+\s*\d{4})', text)
        if match:
            masked = re.sub(r'\s+', '', match.group(1))
            result.account_number_masked = f"XXXXXX{masked[-4:]}"

    def _parse_row(self, row: list, filename: str) -> ParsedTransaction | None:
        if not row or len(row) < 6:
            return None

        raw_date = (row[0] or "").strip()
        if not raw_date:
            return None

        try:
            txn_date = datetime.strptime(raw_date, _DATE_FORMAT).date()
        except ValueError:
            return None

        ref_number = (row[1] or "").strip() or None
        particulars = (row[2] or "").strip()
        if not particulars:
            return None

        amount_str = (row[5] or "").strip()
        if not amount_str:
            return None

        is_credit = amount_str.startswith("-")
        amount_str = amount_str.lstrip("-")

        try:
            amount = Decimal(amount_str.replace(",", "").strip())
        except InvalidOperation:
            return None

        if amount <= 0:
            return None

        dr_cr = "CR" if is_credit else "DR"

        return ParsedTransaction(
            txn_date=txn_date,
            amount=amount,
            dr_cr=dr_cr,
            description="",
            raw_description=particulars,
            reference_number=ref_number,
            mode="Credit Card",
            source_file=filename,
        )

    def _clean_description(self, raw: str) -> str:
        desc = raw.strip()

        if "Payment Recd" in desc or "Payment Received" in desc:
            return "Credit Card Payment"

        # Remove trailing country code and merchant URL junk
        desc = re.sub(r'\s+IN$', '', desc)
        desc = re.sub(r'HTTP://\S+', '', desc, flags=re.IGNORECASE)

        return desc.strip().title()