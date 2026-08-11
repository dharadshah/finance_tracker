"""
Fund metadata fetched from MFAPI for each scheme in mf_holdings.
Stores category, fund house, asset class — enriches holdings for rebalancing analysis.
One row per unique AMFI scheme code.
"""

from datetime import datetime
from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from finance_tracker.database import Base


class FundMetadata(Base):
    """
    Enriched fund information from MFAPI /mf/{scheme_code}.
    Linked to mf_holdings via kuvera_scheme_name (since mf_holdings.scheme_code
    is a Kuvera internal ID, not the real AMFI code).
    """

    __tablename__ = "fund_metadata"

    __table_args__ = (
        UniqueConstraint("scheme_code", name="uq_fund_metadata_scheme_code"),
        Index("ix_fund_metadata_kuvera_name", "kuvera_scheme_name"),
    )

    id:                  Mapped[int]      = mapped_column(primary_key=True, autoincrement=True)

    # Real AMFI scheme code (e.g. "145552") — from bulk NAV file
    scheme_code:         Mapped[str]      = mapped_column(String(20),  nullable=False)

    # Official AMFI scheme name
    amfi_scheme_name:    Mapped[str]      = mapped_column(String(300), nullable=False)

    # How the scheme appears in mf_holdings.scheme_name (Kuvera name)
    kuvera_scheme_name:  Mapped[str]      = mapped_column(String(300), nullable=False)

    # From MFAPI meta
    fund_house:          Mapped[str | None] = mapped_column(String(200), nullable=True)
    scheme_type:         Mapped[str | None] = mapped_column(String(100), nullable=True)
    scheme_category:     Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Derived from scheme_category
    # Values: Equity / Debt / Hybrid / Gold / International / Other
    asset_class:         Mapped[str | None] = mapped_column(String(50),  nullable=True)

    # Sub-category for finer analysis
    # e.g. "Mid Cap" / "Small Cap" / "Flexi Cap" / "ELSS" / "Short Duration"
    sub_category:        Mapped[str | None] = mapped_column(String(100), nullable=True)

    last_refreshed:      Mapped[datetime]  = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<FundMetadata code={self.scheme_code} "
            f"name={self.kuvera_scheme_name} "
            f"class={self.asset_class}>"
        )