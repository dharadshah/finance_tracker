"""
Repository for alternative investments and their payment records.
No business logic — only DB operations.
"""

import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_tracker.models.alternative_investment import (
    AlternativeInvestment,
    AlternativeInvestmentPayment,
)

logger = logging.getLogger(__name__)


class AlternativeInvestmentRepository:

    def __init__(self, session: Session):
        self._session = session

    # ------------------------------------------------------------------
    # AlternativeInvestment
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        investment_date: date,
        invested_amount: Decimal,
        plan_name: str | None = None,
        num_vehicles: int | None = None,
        per_vehicle_rental: Decimal | None = None,
        monthly_income_expected: Decimal | None = None,
        tenure_months: int | None = None,
        salvage_value: Decimal | None = None,
        total_expected_return: Decimal | None = None,
        yearly_rental_pct: Decimal | None = None,
        bank_account_id: int | None = None,
        notes: str | None = None,
    ) -> AlternativeInvestment:
        inv = AlternativeInvestment(
            name=name,
            investment_date=investment_date,
            invested_amount=invested_amount,
            plan_name=plan_name,
            num_vehicles=num_vehicles,
            per_vehicle_rental=per_vehicle_rental,
            monthly_income_expected=monthly_income_expected,
            tenure_months=tenure_months,
            salvage_value=salvage_value,
            total_expected_return=total_expected_return,
            yearly_rental_pct=yearly_rental_pct,
            bank_account_id=bank_account_id,
            notes=notes,
            is_active=True,
            created_at=datetime.now(),
        )
        self._session.add(inv)
        self._session.flush()
        logger.info("Created alternative investment: %s (id=%d)", name, inv.id)
        return inv

    def get_all(self, active_only: bool = False) -> list[AlternativeInvestment]:
        stmt = select(AlternativeInvestment)
        if active_only:
            stmt = stmt.where(AlternativeInvestment.is_active == True)
        stmt = stmt.order_by(AlternativeInvestment.investment_date.desc())
        return list(self._session.execute(stmt).scalars())

    def get_by_id(self, investment_id: int) -> AlternativeInvestment | None:
        return self._session.get(AlternativeInvestment, investment_id)

    def get_total_invested_by_month(self) -> dict[str, float]:
        """
        Returns {month_key: total_invested} e.g. {"2026-06": 500000.0}
        Used by the MF Investment Tracker to include alternative investments.
        """
        investments = self.get_all()
        result: dict[str, float] = {}
        for inv in investments:
            key = inv.investment_date.strftime("%Y-%m")
            result[key] = result.get(key, 0.0) + float(inv.invested_amount)
        return result

    # ------------------------------------------------------------------
    # AlternativeInvestmentPayment
    # ------------------------------------------------------------------

    def add_payment(
        self,
        investment_id: int,
        payment_date: date,
        amount_received: Decimal,
        payment_month: str | None = None,
        notes: str | None = None,
        icici_txn_ref: str | None = None,
    ) -> AlternativeInvestmentPayment:
        payment = AlternativeInvestmentPayment(
            investment_id=investment_id,
            payment_date=payment_date,
            amount_received=amount_received,
            payment_month=payment_month or payment_date.strftime("%Y-%m"),
            notes=notes,
            icici_txn_ref=icici_txn_ref,
        )
        self._session.add(payment)
        self._session.flush()
        logger.info(
            "Recorded payment of %s for investment_id=%d", amount_received, investment_id
        )
        return payment

    def get_payments(
        self, investment_id: int
    ) -> list[AlternativeInvestmentPayment]:
        stmt = (
            select(AlternativeInvestmentPayment)
            .where(AlternativeInvestmentPayment.investment_id == investment_id)
            .order_by(AlternativeInvestmentPayment.payment_date)
        )
        return list(self._session.execute(stmt).scalars())