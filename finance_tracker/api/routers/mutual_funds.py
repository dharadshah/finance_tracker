from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from sqlalchemy import select
import tempfile, os
from pathlib import Path

from finance_tracker.database import get_session
from finance_tracker.models.investment import MFTransaction, MFHolding
from finance_tracker.services.mf_import_service import MFImportService
from finance_tracker.services.nav_fetcher import NAVFetcher


router = APIRouter(prefix="/api/mf", tags=["mutual_funds"])


class MFTransactionResponse(BaseModel):
    id: int
    folio_number: str
    scheme_name: str
    txn_date: date
    order_type: str
    units: float
    nav: float
    current_nav: float
    amount: float

    model_config = {"from_attributes": True}


class MFHoldingResponse(BaseModel):
    id: int
    scheme_name: str
    folio_number: str
    units: float
    avg_nav: float
    invested_amount: float
    current_value: float
    pnl: float
    pnl_pct: float
    last_updated: date

    model_config = {"from_attributes": True}


class MFImportSummaryResponse(BaseModel):
    transactions_inserted: int
    transactions_skipped: int
    holdings_updated: int
    funds_count: int
    period_start: date | None
    period_end: date | None
    warnings: list[str]
    errors: list[str]
    success: bool


@router.post("/import", response_model=MFImportSummaryResponse)
async def import_kuvera(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        service = MFImportService()
        summary = service.import_csv(tmp_path)
    finally:
        os.unlink(tmp_path)

    return MFImportSummaryResponse(
        transactions_inserted=summary.transactions_inserted,
        transactions_skipped=summary.transactions_skipped,
        holdings_updated=summary.holdings_updated,
        funds_count=summary.funds_count,
        period_start=summary.period_start,
        period_end=summary.period_end,
        warnings=summary.warnings,
        errors=summary.errors,
        success=summary.success,
    )


@router.get("/holdings", response_model=list[MFHoldingResponse])
def list_holdings():
    with get_session() as session:
        holdings = session.execute(
            select(MFHolding).order_by(MFHolding.scheme_name)
        ).scalars().all()

        # Get latest NAVs
        fetcher = NAVFetcher()
        latest_navs = fetcher.get_latest_navs(session)

        result = []
        for h in holdings:
            invested = float(h.invested_amount or 0)

            # Use latest NAV if available, else fall back to avg_nav
            nav_match = latest_navs.get(h.scheme_name.lower().strip())
            if nav_match:
                current_nav = float(nav_match[0])
                current_value = float(h.units) * current_nav
            else:
                current_nav = float(h.avg_nav)
                current_value = float(h.units) * current_nav

            pnl = current_value - invested
            pnl_pct = (pnl / invested * 100) if invested > 0 else 0

            result.append(MFHoldingResponse(
                id=h.id,
                scheme_name=h.scheme_name,
                folio_number=h.folio_number,
                units=float(h.units),
                avg_nav=float(h.avg_nav),
                invested_amount=invested,
                current_value=current_value,
                pnl=pnl,
                pnl_pct=pnl_pct,
                last_updated=h.last_updated,
            ))
        return result


@router.get("/transactions", response_model=list[MFTransactionResponse])
def list_mf_transactions(
    scheme_name: str | None = None,
    folio: str | None = None,
):
    with get_session() as session:
        stmt = select(MFTransaction).order_by(MFTransaction.txn_date.desc())
        if scheme_name:
            stmt = stmt.where(MFTransaction.scheme_name.ilike(f"%{scheme_name}%"))
        if folio:
            stmt = stmt.where(MFTransaction.folio_number == folio)
        txns = session.execute(stmt).scalars().all()
        return [MFTransactionResponse.model_validate(t) for t in txns]
    

class NAVFetchSummary(BaseModel):
    fetched: int
    matched: int
    already_current: int
    errors: list[str]


@router.post("/nav/refresh", response_model=NAVFetchSummary)
def refresh_nav():
    with get_session() as session:
        fetcher = NAVFetcher()
        summary = fetcher.fetch_and_store(session)
        return NAVFetchSummary(**summary)


@router.get("/nav/latest", response_model=dict)
def get_latest_nav():
    with get_session() as session:
        fetcher = NAVFetcher()
        navs = fetcher.get_latest_navs(session)
        return {k: {"nav": float(v[0]), "date": str(v[1])} for k, v in navs.items()}