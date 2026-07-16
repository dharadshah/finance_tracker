"""
Models for alternative investments (SpeedForce EV, future similar instruments).

AlternativeInvestment  — one row per investment deal
AlternativeInvestmentPayment — one row per rental/return payment received
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_tracker.database import Base


class AlternativeInvestment(Base):
    """
    Tracks a single alternative investment (e.g. SpeedForce EV fleet rental).
    Stores both the investment details and the plan parameters from the term sheet.
    """

    __tablename__ = "alternative_investments"

    id:               Mapped[int]            = mapped_column(primary_key=True, autoincrement=True)
    name:             Mapped[str]            = mapped_column(String(200), nullable=False)
    investment_date:  Mapped[date]           = mapped_column(Date, nullable=False)
    invested_amount:  Mapped[Decimal]        = mapped_column(Numeric(14, 2), nullable=False)
    plan_name:        Mapped[str | None]     = mapped_column(String(100), nullable=True)

    # Plan parameters (from term sheet)
    num_vehicles:             Mapped[int | None]     = mapped_column(nullable=True)
    per_vehicle_rental:       Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    monthly_income_expected:  Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    tenure_months:            Mapped[int | None]     = mapped_column(nullable=True)
    salvage_value:            Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_expected_return:    Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    yearly_rental_pct:        Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Link to bank account (ICICI) — soft link, no FK constraint
    bank_account_id:  Mapped[int | None]     = mapped_column(nullable=True)

    notes:     Mapped[str | None]  = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool]        = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime]   = mapped_column(DateTime, nullable=False)

    payments: Mapped[list["AlternativeInvestmentPayment"]] = relationship(
        back_populates="investment", cascade="all, delete-orphan"
    )

    @property
    def total_received(self) -> Decimal:
        return sum((p.amount_received for p in self.payments), Decimal("0"))

    @property
    def months_elapsed(self) -> int:
        today = date.today()
        delta = (today.year - self.investment_date.year) * 12 + (
            today.month - self.investment_date.month
        )
        return max(0, delta)

    @property
    def months_remaining(self) -> int:
        if not self.tenure_months:
            return 0
        return max(0, self.tenure_months - self.months_elapsed)

    def __repr__(self) -> str:
        return f"<AlternativeInvestment name={self.name} amount={self.invested_amount}>"


class AlternativeInvestmentPayment(Base):
    """
    One row per rental/return payment received from an alternative investment.
    Linked back to the bank transaction when available.
    """

    __tablename__ = "alternative_investment_payments"

    __table_args__ = (
        Index("ix_alt_payment_investment", "investment_id"),
        Index("ix_alt_payment_date", "payment_date"),
    )

    id:            Mapped[int]          = mapped_column(primary_key=True, autoincrement=True)
    investment_id: Mapped[int]          = mapped_column(
        ForeignKey("alternative_investments.id", ondelete="CASCADE"), nullable=False
    )
    payment_date:     Mapped[date]          = mapped_column(Date, nullable=False)
    amount_received:  Mapped[Decimal]       = mapped_column(Numeric(10, 2), nullable=False)
    payment_month:    Mapped[str | None]    = mapped_column(String(10), nullable=True)  # "2026-08"
    notes:            Mapped[str | None]    = mapped_column(String(300), nullable=True)
    icici_txn_ref:    Mapped[str | None]    = mapped_column(String(100), nullable=True)

    investment: Mapped["AlternativeInvestment"] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        return (
            f"<AltInvestmentPayment investment_id={self.investment_id} "
            f"date={self.payment_date} amount={self.amount_received}>"
        )