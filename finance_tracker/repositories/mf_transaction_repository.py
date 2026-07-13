import logging
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from finance_tracker.models.investment import MFTransaction
from finance_tracker.parsers.base import ParsedMFTransaction

logger = logging.getLogger(__name__)


class MFTransactionRepository:
    """
    All database reads and writes for MF transactions.
    No business logic here — only DB operations.
    """

    def __init__(self, session: Session):
        self._session = session

    def save_parsed_mf_transactions(
        self,
        parsed: list[ParsedMFTransaction],
        account_id: int,
    ) -> tuple[int, int]:
        inserted = 0
        skipped  = 0

        for p in parsed:
            if self._is_duplicate(p):
                skipped += 1
                continue

            txn = MFTransaction(
                account_id=account_id,
                txn_date=p.txn_date,
                scheme_name=p.scheme_name,
                folio_number=p.folio_number,
                txn_type=p.txn_type,
                direction=p.direction,
                units=p.units,
                amount=p.amount,
                source_file=p.source_file or "",
                imported_at=datetime.now(),
            )
            self._session.add(txn)
            inserted += 1

        self._session.flush()
        logger.info(
            "MF Transactions: %d inserted, %d skipped as duplicates",
            inserted,
            skipped,
        )
        return inserted, skipped

    def _is_duplicate(self, p: ParsedMFTransaction) -> bool:
        """
        Duplicate key: folio_number + txn_date + txn_type + units.
        Matches the UniqueConstraint defined on MFTransaction.
        """
        stmt = select(MFTransaction.id).where(
            and_(
                MFTransaction.folio_number == p.folio_number,
                MFTransaction.txn_date    == p.txn_date,
                MFTransaction.txn_type    == p.txn_type,
                MFTransaction.units       == p.units,
            )
        ).limit(1)
        return self._session.execute(stmt).scalar() is not None

    def get_by_account(
        self,
        account_id: int,
        from_date: date | None = None,
        to_date:   date | None = None,
    ) -> list[MFTransaction]:
        stmt = select(MFTransaction).where(
            MFTransaction.account_id == account_id
        )
        if from_date:
            stmt = stmt.where(MFTransaction.txn_date >= from_date)
        if to_date:
            stmt = stmt.where(MFTransaction.txn_date <= to_date)
        stmt = stmt.order_by(MFTransaction.txn_date)
        return list(self._session.execute(stmt).scalars())

    def get_by_folio(self, folio_number: str) -> list[MFTransaction]:
        stmt = (
            select(MFTransaction)
            .where(MFTransaction.folio_number == folio_number)
            .order_by(MFTransaction.txn_date)
        )
        return list(self._session.execute(stmt).scalars())