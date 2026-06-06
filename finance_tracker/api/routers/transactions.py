from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date
from sqlalchemy import select, and_

from finance_tracker.database import get_session
from finance_tracker.models import Transaction, Account, Category
from finance_tracker.models.categorisation import CategorizationLog
from finance_tracker.repositories.transaction_repository import TransactionRepository
from finance_tracker.services.categorisation.pipeline import CategorizationPipeline

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


# Schemas
class TransactionResponse(BaseModel):
    id: int
    account_id: int
    account_name: str
    txn_date: date
    amount: float
    dr_cr: str
    description: str
    category: str | None
    reference_number: str | None
    notes: str | None
    source_file: str | None
    categorisation_source: str | None
    parent_category: str | None
    txn_type: str | None

    model_config = {"from_attributes": True}


class CategoryCorrection(BaseModel):
    category_name: str


class BulkDeleteRequest(BaseModel):
    transaction_ids: list[int]


class BulkCategoryCorrection(BaseModel):
    transaction_ids: list[int]
    category_name: str


# Routes
@router.get("/", response_model=list[TransactionResponse])
def list_transactions(
    account_id: int | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    dr_cr: str | None = Query(None),
    search: str | None = Query(None),
    category: str | None = Query(None),
):
    with get_session() as session:
        stmt = select(Transaction, Account).join(
            Account, Transaction.account_id == Account.id
        )
        if account_id:
            stmt = stmt.where(Transaction.account_id == account_id)
        if from_date:
            stmt = stmt.where(Transaction.txn_date >= from_date)
        if to_date:
            stmt = stmt.where(Transaction.txn_date <= to_date)
        if dr_cr:
            stmt = stmt.where(Transaction.dr_cr == dr_cr)
        if search:
            stmt = stmt.where(Transaction.description.ilike(f"%{search}%"))
        if category:
            stmt = stmt.where(Transaction.category == category)
        stmt = stmt.order_by(Transaction.txn_date.desc())
        rows = session.execute(stmt).all()

        # Build categorisation source map
        log_subq = (
            select(
                CategorizationLog.transaction_id,
                CategorizationLog.source,
            )
            .distinct(CategorizationLog.transaction_id)
            .order_by(
                CategorizationLog.transaction_id,
                CategorizationLog.assigned_at.desc(),
            )
            .subquery()
        )
        log_map = {
            row.transaction_id: row.source
            for row in session.execute(select(log_subq)).all()
        }

        # Build category map
        cat_map = {
            c.name: (c.parent_name or c.name, c.txn_type)
            for c in session.execute(select(Category)).scalars()
        }

        result = []
        for txn, acct in rows:
            parent, txn_type = cat_map.get(txn.category or "Uncategorised", ("Other", "expense"))
            result.append(TransactionResponse(
                id=txn.id,
                account_id=txn.account_id,
                account_name=acct.name,
                txn_date=txn.txn_date,
                amount=float(txn.amount),
                dr_cr=txn.dr_cr,
                description=txn.description,
                category=txn.category,
                reference_number=txn.reference_number,
                notes=txn.notes,
                source_file=txn.source_file,
                categorisation_source=log_map.get(txn.id),
                parent_category=parent,
                txn_type=txn_type,
            ))
        return result


@router.patch("/{transaction_id}/category", response_model=dict)
def correct_category(transaction_id: int, payload: CategoryCorrection):
    with get_session() as session:
        txn = session.get(Transaction, transaction_id)
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")
        acct = session.get(Account, txn.account_id)
        pipeline = CategorizationPipeline(session, acct.institution)
        pipeline.apply_manual_correction(transaction_id, payload.category_name)
        return {"message": f"Category updated to '{payload.category_name}'"}


@router.post("/bulk-correct", response_model=dict)
def bulk_correct_category(payload: BulkCategoryCorrection):
    with get_session() as session:
        for txn_id in payload.transaction_ids:
            txn = session.get(Transaction, txn_id)
            if not txn:
                continue
            acct = session.get(Account, txn.account_id)
            pipeline = CategorizationPipeline(session, acct.institution)
            pipeline.apply_manual_correction(txn_id, payload.category_name)
    return {"message": f"Updated {len(payload.transaction_ids)} transaction(s)"}


@router.post("/bulk-delete", response_model=dict)
def bulk_delete(payload: BulkDeleteRequest):
    with get_session() as session:
        repo = TransactionRepository(session)
        deleted = repo.delete_by_ids(payload.transaction_ids)
    return {"message": f"Deleted {deleted} transaction(s)"}


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int):
    with get_session() as session:
        txn = session.get(Transaction, transaction_id)
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")
        session.delete(txn)
        session.flush()