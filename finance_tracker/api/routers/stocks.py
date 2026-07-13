from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from datetime import date
from sqlalchemy import select
import tempfile, os
from pathlib import Path
from finance_tracker.services.stock_price_fetcher import StockPriceFetcher

from finance_tracker.database import get_session
from finance_tracker.models.investment import StockTransaction, StockHolding, StockPriceHistory
from finance_tracker.models.account import Account
from finance_tracker.services.stock_import_service import StockImportService
from finance_tracker.services.xirr import xirr as calculate_xirr

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


class StockImportSummaryResponse(BaseModel):
    transactions_inserted: int
    transactions_skipped: int
    holdings_updated: int
    symbols_count: int
    period_start: date | None
    period_end: date | None
    warnings: list[str]
    errors: list[str]
    success: bool


class StockHoldingResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    company_name: str | None
    quantity: float
    avg_buy_price: float
    invested_value: float
    current_price: float | None
    current_value: float | None
    pnl: float | None
    pnl_pct: float | None
    xirr: float | None
    last_updated: date

    model_config = {"from_attributes": True}


class StockTransactionResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    trade_date: date
    trade_type: str
    quantity: float
    price: float
    amount: float
    trade_id: str

    model_config = {"from_attributes": True}


class PriceUpdateRequest(BaseModel):
    prices: dict[str, float]  # symbol -> price


@router.post("/import", response_model=StockImportSummaryResponse)
async def import_tradebook(
    file: UploadFile = File(...),
    account_id: int = Form(...),
):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        service = StockImportService()
        summary = service.import_csv(tmp_path, account_id=account_id)
    finally:
        os.unlink(tmp_path)

    return StockImportSummaryResponse(
        transactions_inserted=summary.transactions_inserted,
        transactions_skipped=summary.transactions_skipped,
        holdings_updated=summary.holdings_updated,
        symbols_count=summary.symbols_count,
        period_start=summary.period_start,
        period_end=summary.period_end,
        warnings=summary.warnings,
        errors=summary.errors,
        success=summary.success,
    )


@router.get("/holdings", response_model=list[StockHoldingResponse])
def list_holdings(owner: str | None = None):
    with get_session() as session:
        stmt = select(StockHolding)
        if owner:
            account_ids = [
                a.id for a in session.execute(
                    select(Account).where(Account.owner == owner)
                ).scalars().all()
            ]
            stmt = stmt.where(StockHolding.account_id.in_(account_ids))

        holdings = session.execute(
            stmt.order_by(StockHolding.symbol)
        ).scalars().all()

        # Get latest prices
        price_map = {}
        for h in holdings:
            latest = session.execute(
                select(StockPriceHistory).where(
                    StockPriceHistory.symbol == h.symbol,
                    StockPriceHistory.exchange == h.exchange,
                ).order_by(StockPriceHistory.price_date.desc()).limit(1)
            ).scalar()
            if latest:
                price_map[(h.symbol, h.exchange)] = float(latest.close_price)

        # Load transactions for XIRR
        all_txns = session.execute(
            select(StockTransaction).order_by(StockTransaction.trade_date)
        ).scalars().all()

        from collections import defaultdict
        txn_map = defaultdict(list)
        for t in all_txns:
            txn_map[(t.symbol, t.exchange)].append(t)

        result = []
        today = date.today()
        for h in holdings:
            invested = float(h.quantity) * float(h.avg_buy_price)
            current_price = price_map.get((h.symbol, h.exchange))
            current_value = float(h.quantity) * current_price if current_price else None
            pnl = current_value - invested if current_value is not None else None
            pnl_pct = (pnl / invested * 100) if pnl is not None and invested > 0 else None

            # XIRR
            txns = txn_map.get((h.symbol, h.exchange), [])
            cashflows = []
            for t in txns:
                if t.trade_type == "buy":
                    cashflows.append((t.trade_date, -float(t.quantity * t.price)))
                elif t.trade_type == "sell":
                    cashflows.append((t.trade_date, float(t.quantity * t.price)))
            if cashflows and current_value:
                cashflows.append((today, current_value))
            xirr_value = calculate_xirr(cashflows) if len(cashflows) >= 2 else None

            result.append(StockHoldingResponse(
                id=h.id,
                symbol=h.symbol,
                exchange=h.exchange,
                company_name=h.company_name,
                quantity=float(h.quantity),
                avg_buy_price=float(h.avg_buy_price),
                invested_value=invested,
                current_price=current_price,
                current_value=current_value,
                pnl=pnl,
                pnl_pct=pnl_pct,
                xirr=xirr_value,
                last_updated=h.last_updated,
            ))
        return result


@router.get("/transactions", response_model=list[StockTransactionResponse])
def list_transactions(symbol: str | None = None, owner: str | None = None):
    with get_session() as session:
        stmt = select(StockTransaction).order_by(StockTransaction.trade_date.desc())
        if symbol:
            stmt = stmt.where(StockTransaction.symbol == symbol)
        if owner:
            account_ids = [
                a.id for a in session.execute(
                    select(Account).where(Account.owner == owner)
                ).scalars().all()
            ]
            stmt = stmt.where(StockTransaction.account_id.in_(account_ids))
        txns = session.execute(stmt).scalars().all()
        return [StockTransactionResponse(
            id=t.id,
            symbol=t.symbol,
            exchange=t.exchange,
            trade_date=t.trade_date,
            trade_type=t.trade_type,
            quantity=float(t.quantity),
            price=float(t.price),
            amount=float(t.quantity * t.price),
            trade_id=t.trade_id,
        ) for t in txns]


@router.post("/prices", response_model=dict)
def update_prices(payload: PriceUpdateRequest):
    """Manually update current prices for stocks."""
    with get_session() as session:
        today = date.today()
        updated = 0
        for symbol, price in payload.prices.items():
            # Find exchange for this symbol
            holding = session.execute(
                select(StockHolding).where(StockHolding.symbol == symbol)
            ).scalar()
            if not holding:
                continue
            existing = session.execute(
                select(StockPriceHistory).where(
                    StockPriceHistory.symbol == symbol,
                    StockPriceHistory.exchange == holding.exchange,
                    StockPriceHistory.price_date == today,
                )
            ).scalar()
            if existing:
                existing.close_price = price
            else:
                session.add(StockPriceHistory(
                    symbol=symbol,
                    exchange=holding.exchange,
                    price_date=today,
                    close_price=price,
                ))
            updated += 1
        session.flush()
    return {"message": f"Updated prices for {updated} stocks"}

class PriceFetchSummary(BaseModel):
    fetched: int
    failed: int
    already_current: int
    errors: list[str]

@router.post("/prices/refresh", response_model=PriceFetchSummary)
def refresh_prices():
    with get_session() as session:
        fetcher = StockPriceFetcher()
        summary = fetcher.fetch_and_store(session)
        return PriceFetchSummary(**summary)