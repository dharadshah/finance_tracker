import csv
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance_tracker.database import get_session
from finance_tracker.models.investment import MFTransaction, MFHolding
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

_DATE_FORMAT = "%Y-%m-%d"


@dataclass
class MFImportSummary:
    transactions_inserted: int = 0
    transactions_skipped: int = 0
    holdings_updated: int = 0
    funds_count: int = 0
    period_start: date | None = None
    period_end: date | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_processed(self) -> int:
        return self.transactions_inserted + self.transactions_skipped


class MFImportService:
    """
    Imports Kuvera CSV transactions into mf_transactions table.
    Also updates mf_holdings (units, avg_nav, invested_amount) per fund.
    """

    def import_csv(self, file_path: str | Path, account_id: int) -> MFImportSummary:
        path = Path(file_path)
        summary = MFImportSummary()

        try:
            raw_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except Exception as e:
            summary.errors.append(f"Could not read file: {e}")
            return summary

        if not raw_lines:
            summary.errors.append("File is empty")
            return summary

        # Parse CSV
        reader = csv.DictReader(raw_lines)
        reader.fieldnames = [f.strip() for f in reader.fieldnames]
        rows = list(reader)

        with get_session() as session:
            for row in rows:
                try:
                    inserted = self._process_row(session, row, path.name)
                    if inserted:
                        summary.transactions_inserted += 1
                    else:
                        summary.transactions_skipped += 1
                except Exception as e:
                    summary.warnings.append(f"Skipped row: {e}")

            # Rebuild holdings from all transactions
            summary.holdings_updated = self._rebuild_holdings(session, account_id)

        # Set period
        if rows:
            dates = []
            for row in rows:
                try:
                    from datetime import datetime
                    dates.append(datetime.strptime(row.get("Date", "").strip(), _DATE_FORMAT).date())
                except ValueError:
                    pass
            if dates:
                summary.period_start = min(dates)
                summary.period_end = max(dates)

        summary.funds_count = len({r.get("Name of the Fund", "").strip() for r in rows})
        return summary

    def _process_row(self, session, row: dict, filename: str) -> bool:
        raw_date = row.get("Date", "").strip()
        folio = row.get("Folio Number", "").strip()
        scheme = row.get("Name of the Fund", "").strip()
        order = row.get("Order", "").strip().lower()
        units = self._to_decimal(row.get("Units", ""))
        nav = self._to_decimal(row.get("NAV", ""))
        current_nav = self._to_decimal(row.get("Current Nav", ""))
        amount = self._to_decimal(row.get("Amount (INR)", ""))

        if not raw_date or not scheme or not folio:
            return False

        from datetime import datetime
        try:
            txn_date = datetime.strptime(raw_date, _DATE_FORMAT).date()
        except ValueError:
            return False

        # Check duplicate
        existing = session.execute(
            select(MFTransaction).where(
                and_(
                    MFTransaction.folio_number == folio,
                    MFTransaction.txn_date == txn_date,
                    MFTransaction.order_type == order,
                    MFTransaction.units == units,
                )
            )
        ).scalar()

        if existing:
            return False

        session.add(MFTransaction(
            folio_number=folio,
            scheme_name=scheme,
            txn_date=txn_date,
            order_type=order,
            units=units,
            nav=nav,
            current_nav=current_nav,
            amount=amount,
            source_file=filename,
        ))
        session.flush()
        return True

    def _rebuild_holdings(self, session, account_id: int) -> int:
        """
        Rebuilds mf_holdings from scratch based on all mf_transactions.
        Units = sum of buys - sum of sells per folio+scheme.
        """
        # Find Kuvera account
        from finance_tracker.models.account import Account
        kuvera_account = session.execute(
            select(Account).where(Account.institution == "Kuvera")
        ).scalar()
        if not kuvera_account:
            logger.warning("No Kuvera account found — holdings will not be saved")
            return 0
        account_id = kuvera_account.id
        
        # Load all transactions
        txns = session.execute(select(MFTransaction)).scalars().all()

        # Group by folio + scheme
        holdings_map: dict[tuple, dict] = {}
        for t in txns:
            key = (t.folio_number, t.scheme_name)
            if key not in holdings_map:
                holdings_map[key] = {
                    "units": Decimal("0"),
                    "invested": Decimal("0"),
                    "latest_nav": t.current_nav,
                    "last_date": t.txn_date,
                }
            h = holdings_map[key]
            if t.order_type == "buy":
                h["units"] += t.units
                h["invested"] += t.amount
            elif t.order_type == "sell":
                h["units"] -= t.units
                h["invested"] -= t.amount
            if t.txn_date >= h["last_date"]:
                h["latest_nav"] = t.current_nav
                h["last_date"] = t.txn_date

        # Delete all existing holdings and recreate
        from sqlalchemy import delete
        session.execute(delete(MFHolding).where(MFHolding.account_id == account_id))
        
        from datetime import date as date_type
        today = date_type.today()

        for (folio, scheme), h in holdings_map.items():
            if h["units"] <= 0:
                continue  # fully redeemed
            avg_nav = h["invested"] / h["units"] if h["units"] > 0 else Decimal("0")
            session.add(MFHolding(
                account_id=account_id,  # will be updated when we add account selection
                scheme_code=f"{folio}_{scheme[:20]}",  # using folio as scheme code for now
                scheme_name=scheme,
                folio_number=folio,
                units=h["units"],
                avg_nav=avg_nav,
                invested_amount=h["invested"],
                last_updated=today,
            ))

        session.flush()
        return len(holdings_map)

    @staticmethod
    def _to_decimal(value: str) -> Decimal:
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return Decimal("0")
        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal("0")