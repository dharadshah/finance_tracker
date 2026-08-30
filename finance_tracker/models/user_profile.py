"""
User risk profile for portfolio rebalancing recommendations.
One row per owner. The LLM agent reads this at runtime to
personalise its analysis and recommendations.
"""

from sqlalchemy import String, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal

from finance_tracker.database import Base


class UserProfile(Base):
    """
    Stores investment profile for one owner.
    Target allocations are optional — if null, the agent
    derives them from age and risk_tolerance.
    """

    __tablename__ = "user_profiles"

    id:    Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # Personal context
    age:                Mapped[int | None]     = mapped_column(Integer,  nullable=True)
    risk_tolerance:     Mapped[str | None]     = mapped_column(String(20), nullable=True)
    # Values: conservative / moderate / aggressive
    investment_horizon: Mapped[int | None]     = mapped_column(Integer,  nullable=True)
    # Years until you need this money

    # Target allocation (percentages, should sum to 100)
    # If null, agent derives from age + risk_tolerance
    target_equity_pct:         Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    target_debt_pct:           Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    target_gold_pct:           Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    target_international_pct:  Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    target_other_pct:          Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<UserProfile owner={self.owner} "
            f"age={self.age} risk={self.risk_tolerance}>"
        )