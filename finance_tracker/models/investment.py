from sqlalchemy import String, Date, Numeric, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from decimal import Decimal

from finance_tracker.database import Base


class MFHolding(Base):
    """
    Current mutual fund units held per folio per scheme.
    Units and average NAV are updated on each import run.
    Current value is computed at query time: units * latest NAV from mf_nav_history.
    """

    __tablename__ = "mf_holdings"

    __table_args__ = (
        UniqueConstraint("account_id", "scheme_code", "folio_number", name="uq_mf_holding"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    scheme_code: Mapped[str] = mapped_column(String(20), nullable=False)
    scheme_name: Mapped[str] = mapped_column(String(300), nullable=False)
    folio_number: Mapped[str] = mapped_column(String(50), nullable=False)
    units: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    avg_nav: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    invested_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    last_updated: Mapped[date] = mapped_column(Date, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="mf_holdings")  # noqa: F821

    @property
    def cost_value(self) -> Decimal:
        return self.units * self.avg_nav

    def __repr__(self) -> str:
        return f"<MFHolding scheme={self.scheme_code} units={self.units} folio={self.folio_number}>"


class MFNavHistory(Base):
    """
    Daily NAV values fetched from MFAPI (api.mfapi.in).
    Stored locally so XIRR and return calculations do not need a live API call.
    scheme_code is the 6-digit MFAPI identifier.
    """

    __tablename__ = "mf_nav_history"

    __table_args__ = (
        UniqueConstraint("scheme_code", "nav_date", name="uq_nav_date"),
        Index("ix_nav_history_scheme_date", "scheme_code", "nav_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scheme_code: Mapped[str] = mapped_column(String(20), nullable=False)
    scheme_name: Mapped[str] = mapped_column(String(300), nullable=False)
    nav_date: Mapped[date] = mapped_column(Date, nullable=False)
    nav: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    def __repr__(self) -> str:
        return f"<MFNavHistory scheme={self.scheme_code} date={self.nav_date} nav={self.nav}>"


class StockHolding(Base):
    """
    Current equity positions from broker (Zerodha / Groww).
    Quantity and average buy price updated on each import run.
    Current price fetched live at dashboard render time.
    """

    __tablename__ = "stock_holdings"

    __table_args__ = (
        UniqueConstraint("account_id", "symbol", "exchange", name="uq_stock_holding"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False, default="NSE")
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    avg_buy_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    last_updated: Mapped[date] = mapped_column(Date, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="stock_holdings")  # noqa: F821

    @property
    def invested_value(self) -> Decimal:
        return self.quantity * self.avg_buy_price

    def __repr__(self) -> str:
        return f"<StockHolding symbol={self.symbol} qty={self.quantity} avg={self.avg_buy_price}>"
