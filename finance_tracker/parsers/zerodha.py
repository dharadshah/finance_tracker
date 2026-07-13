import csv
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from finance_tracker.parsers.base import BaseStatementParser, ParseResult, ParsedTransaction

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%Y-%m-%d"


class ZerodhaParser(BaseStatementParser):
    """
    Parser for Zerodha Tradebook CSV exports.
    Columns: symbol, isin, trade_date, exchange, segment, series,
             trade_type, auction, quantity, price, trade_id, order_id,
             order_execution_time
    """

    INSTITUTION = "Zerodha"

    def parse(self, file_path: Path) -> ParseResult:
        result = ParseResult(institution=self.INSTITUTION)

        try:
            raw_lines = file_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except Exception as e:
            result.errors.append(f"Could not read file: {e}")
            return result

        reader = csv.DictReader(raw_lines)
        dates = []

        for row in reader:
            try:
                txn = self._parse_row(row, file_path.name)
                if txn:
                    result.transactions.append(txn)
                    dates.append(txn.txn_date)
            except Exception as e:
                result.warnings.append(f"Skipped row: {row} — {e}")

        if dates:
            result.statement_period_start = min(dates)
            result.statement_period_end = max(dates)

        logger.info(
            "Zerodha parser: %d trades from %s",
            result.transaction_count,
            file_path.name,
        )
        return result

    def _parse_row(self, row: dict, filename: str) -> ParsedTransaction | None:
        symbol = row.get("symbol", "").strip()
        isin = row.get("isin", "").strip()
        trade_date_str = row.get("trade_date", "").strip()
        exchange = row.get("exchange", "").strip()
        trade_type = row.get("trade_type", "").strip().lower()
        quantity = row.get("quantity", "").strip()
        price = row.get("price", "").strip()
        trade_id = row.get("trade_id", "").strip()
        order_id = row.get("order_id", "").strip()

        if not symbol or not trade_date_str:
            return None

        try:
            trade_date = datetime.strptime(trade_date_str, _DATE_FORMAT).date()
        except ValueError:
            return None

        qty = self._to_decimal(quantity)
        prc = self._to_decimal(price)
        amount = qty * prc

        dr_cr = "DR" if trade_type == "buy" else "CR"

        # Store all stock-specific data in raw_description
        raw_desc = f"{trade_id}|{isin}|{exchange}|{trade_type}|{qty}|{prc}"

        return ParsedTransaction(
            txn_date=trade_date,
            amount=amount,
            dr_cr=dr_cr,
            description=f"{trade_type.title()} / {symbol}",
            raw_description=raw_desc,
            reference_number=trade_id,
            mode=exchange,
            source_file=filename,
        )

    def _clean_description(self, raw: str) -> str:
        return raw  # already clean