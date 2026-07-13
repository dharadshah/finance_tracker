import csv
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, delete

from finance_tracker.database import get_session
from finance_tracker.models.investment import StockTransaction, StockHolding

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%Y-%m-%d"


@dataclass
class StockImportSummary:
    transactions_inserted: int = 0
    transactions_skipped: int = 0
    holdings_updated: int = 0
    symbols_count: int = 0
    period_start: date | None = None
    period_end: date | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class StockImportService:
    """
    Imports Zerodha tradebook CSV into stock_transactions.
    Rebuilds stock_holdings from all transactions.
    """

    def import_csv(self, file_path: str | Path, account_id: int) -> StockImportSummary:
        path = Path(file_path)
        summary = StockImportSummary()

        try:
            raw_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except Exception as e:
            summary.errors.append(f"Could not read file: {e}")
            return summary

        reader = csv.DictReader(raw_lines)
        rows = list(reader)

        with get_session() as session:
            for row in rows:
                try:
                    inserted = self._process_row(session, row, account_id, path.name)
                    if inserted:
                        summary.transactions_inserted += 1
                    else:
                        summary.transactions_skipped += 1
                except Exception as e:
                    summary.warnings.append(f"Skipped: {e}")

            summary.holdings_updated = self._rebuild_holdings(session, account_id)

        # Set period
        dates = []
        for row in rows:
            try:
                from datetime import datetime
                dates.append(datetime.strptime(row.get("trade_date", "").strip(), _DATE_FORMAT).date())
            except ValueError:
                pass
        if dates:
            summary.period_start = min(dates)
            summary.period_end = max(dates)

        summary.symbols_count = len({r.get("symbol", "").strip() for r in rows})
        return summary

    def _process_row(self, session, row: dict, account_id: int, filename: str) -> bool:
        from datetime import datetime

        symbol = row.get("symbol", "").strip()
        isin = row.get("isin", "").strip()
        trade_date_str = row.get("trade_date", "").strip()
        exchange = row.get("exchange", "NSE").strip()
        trade_type = row.get("trade_type", "").strip().lower()
        quantity = Decimal(row.get("quantity", "0").strip())
        price = Decimal(row.get("price", "0").strip())
        trade_id = row.get("trade_id", "").strip()
        order_id = row.get("order_id", "").strip() or None

        if not symbol or not trade_date_str or not trade_id:
            return False

        trade_date = datetime.strptime(trade_date_str, _DATE_FORMAT).date()

        # Check duplicate
        existing = session.execute(
            select(StockTransaction).where(StockTransaction.trade_id == trade_id)
        ).scalar()
        if existing:
            return False

        session.add(StockTransaction(
            account_id=account_id,
            symbol=symbol,
            isin=isin or None,
            exchange=exchange,
            trade_date=trade_date,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            trade_id=trade_id,
            order_id=order_id,
            source_file=filename,
        ))
        session.flush()
        return True

    def _rebuild_holdings(self, session, account_id: int) -> int:
        """Rebuild stock holdings from all transactions for this account."""
        txns = session.execute(
            select(StockTransaction).where(
                StockTransaction.account_id == account_id
            ).order_by(StockTransaction.trade_date)
        ).scalars().all()

        # Group by symbol + exchange
        holdings_map = {}
        for t in txns:
            key = (t.symbol, t.exchange)
            if key not in holdings_map:
                holdings_map[key] = {
                    "quantity": Decimal("0"),
                    "total_cost": Decimal("0"),
                    "isin": t.isin,
                }
            h = holdings_map[key]
            if t.trade_type == "buy":
                h["total_cost"] += t.quantity * t.price
                h["quantity"] += t.quantity
            elif t.trade_type == "sell":
                # Reduce avg cost proportionally
                if h["quantity"] > 0:
                    avg = h["total_cost"] / h["quantity"]
                    h["total_cost"] -= avg * t.quantity
                h["quantity"] -= t.quantity

        # Delete existing holdings for this account
        session.execute(
            delete(StockHolding).where(StockHolding.account_id == account_id)
        )

        today = date.today()
        count = 0
        for (symbol, exchange), h in holdings_map.items():
            if h["quantity"] <= Decimal("0.001"):
                continue  # fully sold
            avg_price = h["total_cost"] / h["quantity"] if h["quantity"] > 0 else Decimal("0")
            session.add(StockHolding(
                account_id=account_id,
                symbol=symbol,
                exchange=exchange,
                company_name=None,
                quantity=h["quantity"],
                avg_buy_price=avg_price,
                last_updated=today,
            ))
            count += 1

        session.flush()
        return count