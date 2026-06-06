import csv
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from finance_tracker.parsers.base import BaseStatementParser, ParseResult, ParsedTransaction

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%Y-%m-%d"


class KuveraParser(BaseStatementParser):
    """
    Parser for Kuvera mutual fund transaction CSV exports.

    CSV format:
    Date, Folio Number, Name of the Fund, Order, Units, NAV, Current Nav, Amount (INR)
    """

    INSTITUTION = "Kuvera"

    def parse(self, file_path: Path) -> ParseResult:
        result = ParseResult(institution=self.INSTITUTION)

        try:
            raw_lines = file_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except Exception as e:
            result.errors.append(f"Could not read file: {e}")
            return result

        if not raw_lines:
            result.errors.append("File is empty")
            return result

        # Parse CSV rows
        reader = csv.DictReader(raw_lines)
        # Normalize headers — strip spaces
        reader.fieldnames = [f.strip() for f in reader.fieldnames]

        for row in reader:
            try:
                txn = self._parse_row(row, file_path.name)
                if txn:
                    result.transactions.append(txn)
            except Exception as e:
                result.warnings.append(f"Skipped row: {row} — {e}")

        # Set period from transactions
        if result.transactions:
            dates = [t.txn_date for t in result.transactions]
            result.statement_period_start = min(dates)
            result.statement_period_end = max(dates)

        logger.info(
            "Kuvera parser: %d transactions from %s",
            result.transaction_count,
            file_path.name,
        )
        return result

    def _parse_row(self, row: dict, filename: str) -> ParsedTransaction | None:
        raw_date = row.get("Date", "").strip()
        folio = row.get("Folio Number", "").strip()
        scheme = row.get("Name of the Fund", "").strip()
        order = row.get("Order", "").strip().lower()
        units_str = row.get("Units", "").strip()
        nav_str = row.get("NAV", "").strip()
        current_nav_str = row.get("Current Nav", "").strip()
        amount_str = row.get("Amount (INR)", "").strip()

        if not raw_date or not scheme:
            return None

        # Parse date
        try:
            txn_date = datetime.strptime(raw_date, _DATE_FORMAT).date()
        except ValueError:
            return None

        # Parse decimals
        units = self._to_decimal(units_str)
        nav = self._to_decimal(nav_str)
        current_nav = self._to_decimal(current_nav_str)
        amount = self._to_decimal(amount_str)

        # For sells, amount is negative (outflow becomes inflow)
        dr_cr = "DR" if order == "buy" else "CR"

        # Store all MF-specific data in raw_description as pipe-separated
        raw_desc = f"{folio}|{order}|{units}|{nav}|{current_nav}"

        return ParsedTransaction(
            txn_date=txn_date,
            amount=amount,
            dr_cr=dr_cr,
            description=f"{order.title()} / {scheme}",
            raw_description=raw_desc,
            reference_number=folio,
            mode=order,
            source_file=filename,
        )

    def _clean_description(self, raw: str) -> str:
        # Kuvera descriptions are already clean — skip base cleaning
        return raw