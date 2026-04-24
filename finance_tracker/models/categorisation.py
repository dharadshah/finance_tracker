from sqlalchemy import String, DateTime, ForeignKey, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from finance_tracker.database import Base


class CategorizationLog(Base):
    """
    Audit trail for every category assignment on a transaction.
    One row per assignment event — source tells you who assigned it.

    Sources:
        rule     — matched a bank-specific pattern rule
        learned  — matched a previously corrected description
        ollama   — assigned by local Ollama model
        manual   — user corrected it in the UI

    Confidence:
        high    — rule or learned match (deterministic)
        medium  — ollama with clear match
        low     — ollama uncertain or fallback
    """

    __tablename__ = "categorization_log"

    __table_args__ = (
        Index("ix_cat_log_transaction", "transaction_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    category_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # rule | learned | ollama | manual
    confidence: Mapped[str] = mapped_column(
        String(10), nullable=False, default="high"
    )  # high | medium | low
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)

    transaction: Mapped["Transaction"] = relationship()  # noqa: F821
    category: Mapped["Category | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<CategorizationLog txn={self.transaction_id} "
            f"category={self.category_name!r} source={self.source}>"
        )


class LearnedRule(Base):
    """
    Stores description → category mappings learned from manual corrections.
    When a user corrects a category in the UI, we record it here.
    On next import, matching descriptions skip Ollama entirely.

    Scoped per institution so ICICI patterns don't bleed into YES Bank.
    """

    __tablename__ = "learned_rules"

    __table_args__ = (
        UniqueConstraint("institution", "description_pattern", name="uq_learned_rule"),
        Index("ix_learned_rules_institution", "institution"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    institution: Mapped[str] = mapped_column(String(100), nullable=False)
    description_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    category_name: Mapped[str] = mapped_column(String(80), nullable=False)
    match_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    category: Mapped["Category"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<LearnedRule institution={self.institution!r} "
            f"pattern={self.description_pattern!r} → {self.category_name!r}>"
        )
