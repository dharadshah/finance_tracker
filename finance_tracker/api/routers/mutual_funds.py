from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from sqlalchemy import select
import tempfile, os
from pathlib import Path
from finance_tracker.services.nav_fetcher import NAVFetcher, AMFI_URL
import httpx

from finance_tracker.database import get_session
from finance_tracker.models.investment import MFTransaction, MFHolding
from finance_tracker.services.mf_import_service import MFImportService
from finance_tracker.services.nav_fetcher import NAVFetcher
from finance_tracker.services.xirr import xirr as calculate_xirr


router = APIRouter(prefix="/api/mf", tags=["mutual_funds"])


class MFTransactionResponse(BaseModel):
    id:           int
    folio_number: str
    scheme_name:  str
    txn_date:     date
    units:        float
    amount:       float
    order_type:   str | None = None
    nav:          float | None = None
    current_nav:  float | None = None
    txn_type:     str | None = None
    direction:    str | None = None

    model_config = {"from_attributes": True}


class MFHoldingResponse(BaseModel):
    id:             int
    scheme_name:    str
    folio_number:   str
    units:          float
    avg_nav:        float
    invested_amount: float
    current_value:  float
    pnl:            float
    pnl_pct:        float
    xirr:           float | None = None
    last_updated:   date

    model_config = {"from_attributes": True}


class MFImportSummaryResponse(BaseModel):
    transactions_inserted: int
    transactions_skipped:  int
    holdings_updated:      int
    funds_count:           int
    period_start:          date | None
    period_end:            date | None
    warnings: list[str]
    errors:   list[str]
    success:  bool


class NJIndiaImportSummaryResponse(BaseModel):
    transactions_inserted: int
    transactions_skipped:  int
    statement_period:      str
    warnings: list[str]
    errors:   list[str]
    success:  bool


@router.post("/import", response_model=MFImportSummaryResponse)
async def import_kuvera(
    file: UploadFile = File(...),
    account_id: int = Form(...),
):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        service = MFImportService()
        summary = service.import_csv(tmp_path, account_id=account_id)
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


@router.post("/import/nj-india", response_model=NJIndiaImportSummaryResponse)
async def import_nj_india(
    file: UploadFile = File(...),
    account_id: int = Form(None),
):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        from finance_tracker.services.import_service import ImportService
        service = ImportService()
        summary = service.import_mf_transactions(
            file_path=tmp_path,
            parser_key="nj_india",
            account_id=account_id,
        )
    finally:
        os.unlink(tmp_path)

    return NJIndiaImportSummaryResponse(
        transactions_inserted=summary.transactions_inserted,
        transactions_skipped=summary.transactions_skipped,
        statement_period=summary.statement_period,
        warnings=summary.warnings,
        errors=summary.errors,
        success=summary.success,
    )


@router.get("/holdings", response_model=list[MFHoldingResponse])
def list_holdings(owner: str | None = None, account_id: int | None = None):
    with get_session() as session:
        stmt = select(MFHolding)

        if account_id:
            stmt = stmt.where(MFHolding.account_id == account_id)
        elif owner:
            from finance_tracker.models.account import Account
            account_ids = [
                a.id for a in session.execute(
                    select(Account).where(Account.owner == owner)
                ).scalars().all()
            ]
            stmt = stmt.where(MFHolding.account_id.in_(account_ids))

        holdings = session.execute(
            stmt.order_by(MFHolding.scheme_name)
        ).scalars().all()

        fetcher = NAVFetcher()
        latest_navs = fetcher.get_latest_navs(session)

        all_txns = session.execute(
            select(MFTransaction).order_by(MFTransaction.txn_date)
        ).scalars().all()

        from collections import defaultdict
        txn_map = defaultdict(list)
        for t in all_txns:
            txn_map[(t.folio_number, t.scheme_name)].append(t)

        result = []
        today = date.today()

        for h in holdings:
            invested = float(h.invested_amount or 0)

            nav_match = latest_navs.get(h.scheme_name.lower().strip())
            if nav_match:
                current_nav = float(nav_match[0])
                current_value = float(h.units) * current_nav
            else:
                current_nav = float(h.avg_nav)
                current_value = float(h.units) * current_nav

            pnl = current_value - invested
            pnl_pct = (pnl / invested * 100) if invested > 0 else 0

            txns = txn_map.get((h.folio_number, h.scheme_name), [])
            cashflows = []
            for t in txns:
                if t.order_type == "buy":
                    cashflows.append((t.txn_date, -float(t.amount)))
                elif t.order_type == "sell":
                    cashflows.append((t.txn_date, float(t.amount)))
            if cashflows and current_value > 0:
                cashflows.append((today, current_value))

            xirr_value = calculate_xirr(cashflows)

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
                xirr=xirr_value,
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
    fetched:         int
    matched:         int
    already_current: int
    errors:          list[str]


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


@router.get("/nav/debug")
def debug_nav():
    with get_session() as session:
        fetcher = NAVFetcher()
        navs = fetcher.get_latest_navs(session)
        holdings = session.execute(select(MFHolding)).scalars().all()
        return {
            "nav_keys": list(navs.keys())[:5],
            "holding_names": [h.scheme_name.lower().strip() for h in holdings][:5],
        }


@router.get("/nav/search")
def search_nav(q: str):
    try:
        response = httpx.get(AMFI_URL, timeout=30, follow_redirects=True)
        lines = response.text.splitlines()
    except Exception as e:
        return {"error": str(e)}

    matches = []
    for line in lines:
        parts = line.strip().split(";")
        if len(parts) < 6:
            continue
        if q.lower() in parts[3].lower():
            matches.append({"code": parts[0], "name": parts[3], "nav": parts[4]})
    return matches[:20]