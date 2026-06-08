from sqlalchemy import String, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from enum import Enum
from decimal import Decimal
from sqlalchemy import String, Date, Enum as SAEnum, Numeric
from finance_tracker.database import Base


class AccountType(str, Enum):
    SAVINGS = "savings"
    CURRENT = "current"
    CREDIT_CARD = "credit_card"
    DEMAT = "demat"
    MF_FOLIO = "mf_folio"
    WALLET = "wallet"


class Account(Base):
    """
    Master registry of every financial account owned.
    All other tables reference this via account_id.
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(
        SAEnum(AccountType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    current_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    institution: Mapped[str] = mapped_column(String(100), nullable=False)
    account_number_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    opened_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner: Mapped[str] = mapped_column(String(50), default="Dhara", nullable=False)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    credit_card_dues: Mapped[list["CreditCardDue"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    mf_holdings: Mapped[list["MFHolding"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    stock_holdings: Mapped[list["StockHolding"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name!r} type={self.account_type}>"
