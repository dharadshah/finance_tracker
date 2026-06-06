from sqlalchemy import String, Date, Numeric, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from decimal import Decimal
from enum import Enum

from finance_tracker.database import Base


class DrCr(str, Enum):
    DEBIT = "DR"
    CREDIT = "CR"


class Category(Base):
    """
    Lookup table for transaction categories.
    Supports a two-level hierarchy: parent_name > name.
    Example: Food > Dining Out, Transport > Fuel
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    parent_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    txn_type: Mapped[str] = mapped_column(
        String(20), default="expense", nullable=False
    )  # expense | income | transfer | investment

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category_ref")

    def __repr__(self) -> str:
        return f"<Category {self.parent_name}/{self.name}>"


class Transaction(Base):
    """
    Every debit and credit from every bank account and credit card.
    This is the central fact table for all expense and income analysis.

    DR/CR is stored as a string enum to prevent sign-drop bugs during CSV parsing.
    Signed amounts are computed at query time only.
    """

    __tablename__ = "transactions"

    __table_args__ = (
        Index("ix_transactions_account_date", "account_id", "txn_date"),
        Index("ix_transactions_category", "category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    txn_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    dr_cr: Mapped[str] = mapped_column(
        SAEnum(DrCr, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="transactions")  # noqa: F821
    category_ref: Mapped["Category | None"] = relationship(back_populates="transactions")

    @property
    def signed_amount(self) -> Decimal:
        """Returns negative amount for debits, positive for credits."""
        return -self.amount if self.dr_cr == DrCr.DEBIT else self.amount

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} date={self.txn_date} "
            f"{self.dr_cr} {self.amount} {self.description[:30]!r}>"
        )
