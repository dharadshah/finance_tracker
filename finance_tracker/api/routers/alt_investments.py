"""
API router for alternative investments (SpeedForce EV and future similar instruments).
"""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from finance_tracker.database import get_session
from finance_tracker.repositories.alternative_investment_repository import (
    AlternativeInvestmentRepository,
)

router = APIRouter(prefix="/api/alt-investments", tags=["alternative_investments"])


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------

class CreateAltInvestmentRequest(BaseModel):
    name:                    str
    investment_date:         date
    invested_amount:         float
    plan_name:               str | None = None
    num_vehicles:            int | None = None
    per_vehicle_rental:      float | None = None
    monthly_income_expected: float | None = None
    tenure_months:           int | None = None
    salvage_value:           float | None = None
    total_expected_return:   float | None = None
    yearly_rental_pct:       float | None = None
    bank_account_id:         int | None = None
    notes:                   str | None = None


class AltInvestmentResponse(BaseModel):
    id:                      int
    name:                    str
    investment_date:         date
    invested_amount:         float
    plan_name:               str | None
    num_vehicles:            int | None
    per_vehicle_rental:      float | None
    monthly_income_expected: float | None
    tenure_months:           int | None
    salvage_value:           float | None
    total_expected_return:   float | None
    yearly_rental_pct:       float | None
    bank_account_id:         int | None
    notes:                   str | None
    is_active:               bool
    total_received:          float
    months_elapsed:          int
    months_remaining:        int


class AddPaymentRequest(BaseModel):
    payment_date:    date
    amount_received: float
    payment_month:   str | None = None
    notes:           str | None = None
    icici_txn_ref:   str | None = None


class PaymentResponse(BaseModel):
    id:              int
    investment_id:   int
    payment_date:    date
    amount_received: float
    payment_month:   str | None
    notes:           str | None
    icici_txn_ref:   str | None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

def _to_response(inv) -> AltInvestmentResponse:
    return AltInvestmentResponse(
        id=inv.id,
        name=inv.name,
        investment_date=inv.investment_date,
        invested_amount=float(inv.invested_amount),
        plan_name=inv.plan_name,
        num_vehicles=inv.num_vehicles,
        per_vehicle_rental=float(inv.per_vehicle_rental) if inv.per_vehicle_rental else None,
        monthly_income_expected=float(inv.monthly_income_expected) if inv.monthly_income_expected else None,
        tenure_months=inv.tenure_months,
        salvage_value=float(inv.salvage_value) if inv.salvage_value else None,
        total_expected_return=float(inv.total_expected_return) if inv.total_expected_return else None,
        yearly_rental_pct=float(inv.yearly_rental_pct) if inv.yearly_rental_pct else None,
        bank_account_id=inv.bank_account_id,
        notes=inv.notes,
        is_active=inv.is_active,
        total_received=float(inv.total_received),
        months_elapsed=inv.months_elapsed,
        months_remaining=inv.months_remaining,
    )


@router.post("/", response_model=AltInvestmentResponse)
def create_investment(req: CreateAltInvestmentRequest):
    with get_session() as session:
        repo = AlternativeInvestmentRepository(session)
        inv = repo.create(
            name=req.name,
            investment_date=req.investment_date,
            invested_amount=Decimal(str(req.invested_amount)),
            plan_name=req.plan_name,
            num_vehicles=req.num_vehicles,
            per_vehicle_rental=Decimal(str(req.per_vehicle_rental)) if req.per_vehicle_rental else None,
            monthly_income_expected=Decimal(str(req.monthly_income_expected)) if req.monthly_income_expected else None,
            tenure_months=req.tenure_months,
            salvage_value=Decimal(str(req.salvage_value)) if req.salvage_value else None,
            total_expected_return=Decimal(str(req.total_expected_return)) if req.total_expected_return else None,
            yearly_rental_pct=Decimal(str(req.yearly_rental_pct)) if req.yearly_rental_pct else None,
            bank_account_id=req.bank_account_id,
            notes=req.notes,
        )
        return _to_response(inv)


@router.get("/", response_model=list[AltInvestmentResponse])
def list_investments(active_only: bool = False):
    with get_session() as session:
        repo = AlternativeInvestmentRepository(session)
        investments = repo.get_all(active_only=active_only)
        return [_to_response(inv) for inv in investments]


@router.get("/{investment_id}", response_model=AltInvestmentResponse)
def get_investment(investment_id: int):
    with get_session() as session:
        repo = AlternativeInvestmentRepository(session)
        inv = repo.get_by_id(investment_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Investment not found")
        return _to_response(inv)


@router.post("/{investment_id}/payments", response_model=PaymentResponse)
def add_payment(investment_id: int, req: AddPaymentRequest):
    with get_session() as session:
        repo = AlternativeInvestmentRepository(session)
        inv = repo.get_by_id(investment_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Investment not found")
        payment = repo.add_payment(
            investment_id=investment_id,
            payment_date=req.payment_date,
            amount_received=Decimal(str(req.amount_received)),
            payment_month=req.payment_month,
            notes=req.notes,
            icici_txn_ref=req.icici_txn_ref,
        )
        return PaymentResponse.model_validate(payment)


@router.get("/{investment_id}/payments", response_model=list[PaymentResponse])
def list_payments(investment_id: int):
    with get_session() as session:
        repo = AlternativeInvestmentRepository(session)
        inv = repo.get_by_id(investment_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Investment not found")
        payments = repo.get_payments(investment_id)
        return [PaymentResponse.model_validate(p) for p in payments]