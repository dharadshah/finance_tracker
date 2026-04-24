from sqlalchemy import String, Date, Numeric, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from decimal import Decimal
from enum import Enum

from finance_tracker.database import Base


class DueStatus(str, Enum):
    UNPAID = "unpaid"
    PAID_FULL = "paid_full"
    PAID_MINIMUM = "paid_minimum"
    PAID_PARTIAL = "paid_partial"
    OVERDUE = "overdue"


class CreditCardDue(Base):
    """
    Statement-level record for each credit card billing cycle.
    Tracks total due, minimum due, due date, and payment status.
    Separate from transactions — captures the statement-level picture.
    """

    __tablename__ = "credit_card_dues"

    __table_args__ = (
        Index("ix_cc_dues_account_statement", "account_id", "statement_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_due: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    minimum_due: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amount_paid: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(DueStatus, values_callable=lambda x: [e.value for e in x]),
        default=DueStatus.UNPAID,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="credit_card_dues")  # noqa: F821

    @property
    def outstanding(self) -> Decimal:
        paid = self.amount_paid or Decimal("0")
        return max(self.total_due - paid, Decimal("0"))

    def __repr__(self) -> str:
        return (
            f"<CreditCardDue account={self.account_id} "
            f"statement={self.statement_date} due={self.total_due} status={self.status}>"
        )
