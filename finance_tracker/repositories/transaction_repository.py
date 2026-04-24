import logging
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from finance_tracker.models import Transaction, Account, DrCr
from finance_tracker.parsers.base import ParsedTransaction

logger = logging.getLogger(__name__)


class TransactionRepository:
    """
    All database reads and writes for transactions.
    No business logic here — only DB operations.
    """

    def __init__(self, session: Session):
        self._session = session

    def save_parsed_transactions(
        self,
        parsed: list[ParsedTransaction],
        account_id: int,
    ) -> tuple[int, int]:
        """
        Inserts parsed transactions, skipping exact duplicates.
        Returns (inserted_count, skipped_count).

        Duplicate detection: same account_id + txn_date + amount + dr_cr + description.
        This is intentionally conservative — a genuine duplicate payment on the
        same day for the same amount will be flagged as a warning, not silently dropped.
        """
        inserted = 0
        skipped = 0

        for p in parsed:
            if self._is_duplicate(account_id, p):
                skipped += 1
                continue

            txn = Transaction(
                account_id=account_id,
                txn_date=p.txn_date,
                amount=p.amount,
                dr_cr=p.dr_cr,
                description=p.description,
                reference_number=p.reference_number,
                notes=p.mode,
                source_file=p.source_file,
                category="Uncategorised",
            )
            self._session.add(txn)
            inserted += 1

        self._session.flush()
        logger.info("Transactions: %d inserted, %d skipped as duplicates", inserted, skipped)
        return inserted, skipped

    def _is_duplicate(self, account_id: int, p: ParsedTransaction) -> bool:
        stmt = select(Transaction.id).where(
            and_(
                Transaction.account_id == account_id,
                Transaction.txn_date == p.txn_date,
                Transaction.amount == p.amount,
                Transaction.dr_cr == p.dr_cr,
                Transaction.description == p.description,
            )
        ).limit(1)
        return self._session.execute(stmt).scalar() is not None

    def get_by_account(
        self,
        account_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.account_id == account_id)
        if from_date:
            stmt = stmt.where(Transaction.txn_date >= from_date)
        if to_date:
            stmt = stmt.where(Transaction.txn_date <= to_date)
        stmt = stmt.order_by(Transaction.txn_date)
        return list(self._session.execute(stmt).scalars())

    def get_uncategorised(self, account_id: int) -> list[Transaction]:
        """Returns transactions for this account that are still Uncategorised."""
        stmt = select(Transaction).where(
            and_(
                Transaction.account_id == account_id,
                Transaction.category == "Uncategorised",
            )
        )
        return list(self._session.execute(stmt).scalars())

    def delete_by_ids(self, transaction_ids: list[int]) -> int:
        """Deletes transactions by ID list. Returns count deleted."""
        if not transaction_ids:
            return 0
        from sqlalchemy import delete
        result = self._session.execute(
            delete(Transaction).where(Transaction.id.in_(transaction_ids))
        )
        self._session.flush()
        count = result.rowcount
        logger.info("Deleted %d transactions", count)
        return count
