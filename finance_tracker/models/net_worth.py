from sqlalchemy import String, Date, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from decimal import Decimal

from finance_tracker.database import Base


class NetWorthSnapshot(Base):
    """
    One row per monthly review — a point-in-time summary of financial position.
    Written manually at the end of each monthly review session.
    Provides a clean time series for the net worth growth chart.
    """

    __tablename__ = "net_worth_snapshots"

    __table_args__ = (
        UniqueConstraint("snapshot_date", name="uq_snapshot_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    net_worth: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    liquid_assets: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    invested_assets: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<NetWorthSnapshot date={self.snapshot_date} "
            f"net_worth={self.net_worth}>"
        )
