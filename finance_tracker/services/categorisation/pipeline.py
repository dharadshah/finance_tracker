import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from finance_tracker.models import Transaction, Category, CategorizationLog
from finance_tracker.services.categorisation.base import UNMATCHED
from finance_tracker.services.categorisation.rule_categorizer import RuleBasedCategorizer
from finance_tracker.services.categorisation.learned_categorizer import LearnedPatternCategorizer
from finance_tracker.services.categorisation.ollama_categorizer import OllamaCategorizer

logger = logging.getLogger(__name__)


class CategorizationPipeline:
    """
    Chains Layer 1 → Layer 2 → Layer 3 for each transaction.
    Called automatically by ImportService after transactions are saved.

    Layer 1: RuleBasedCategorizer   (bank-specific patterns)
    Layer 2: LearnedPatternCategorizer (user corrections)
    Layer 3: OllamaCategorizer       (local LLM fallback)

    Writes result to:
    - transactions.category (the current assigned category name)
    - categorization_log (full audit trail)
    """

    def __init__(self, session: Session, institution: str):
        self._session = session
        self._institution = institution

        # Load all valid category names once
        self._valid_categories = self._load_category_names()
        self._category_id_map = self._load_category_id_map()

        self._layers = [
            RuleBasedCategorizer(),
            LearnedPatternCategorizer(session),
            OllamaCategorizer(self._valid_categories),
        ]

    def run(self, transactions: list[Transaction]) -> dict[str, int]:
        """
        Categorises a list of Transaction ORM objects in place.
        Returns a summary dict: {source: count}.
        """
        summary: dict[str, int] = {
            "rule": 0, "learned": 0, "ollama": 0, "uncategorised": 0
        }

        for txn in transactions:
            if txn.category and txn.category != "Uncategorised":
                continue  # already categorised — skip

            result = UNMATCHED
            for layer in self._layers:
                candidate = layer.categorize(
                    description=txn.description,
                    institution=self._institution,
                    dr_cr=txn.dr_cr,
                )
                if candidate is not None:
                    result = candidate
                    break

            # Validate category exists in master table
            if result.category_name not in self._valid_categories:
                result = UNMATCHED

            # Write to transaction
            txn.category = result.category_name
            txn.category_id = self._category_id_map.get(result.category_name)

            # Write to audit log
            log_entry = CategorizationLog(
                transaction_id=txn.id,
                category_id=txn.category_id,
                category_name=result.category_name,
                source=result.source,
                confidence=result.confidence,
                assigned_at=datetime.now(timezone.utc),
            )
            self._session.add(log_entry)

            if result.matched:
                summary[result.source] = summary.get(result.source, 0) + 1
            else:
                summary["uncategorised"] += 1

        self._session.flush()
        logger.info(
            "Categorisation complete for %s: %s",
            self._institution,
            ", ".join(f"{k}={v}" for k, v in summary.items() if v > 0),
        )
        return summary

    def apply_manual_correction(
        self,
        transaction_id: int,
        new_category_name: str,
    ) -> None:
        """
        Called when user corrects a category in the UI.
        Updates the transaction, logs the change, and saves a learned rule.
        """
        txn = self._session.get(Transaction, transaction_id)
        if txn is None:
            raise ValueError(f"Transaction {transaction_id} not found.")

        if new_category_name not in self._valid_categories:
            raise ValueError(f"Category {new_category_name!r} not in master table.")

        category_id = self._category_id_map.get(new_category_name)
        txn.category = new_category_name
        txn.category_id = category_id

        self._session.add(CategorizationLog(
            transaction_id=transaction_id,
            category_id=category_id,
            category_name=new_category_name,
            source="manual",
            confidence="high",
            assigned_at=datetime.now(timezone.utc),
            notes="User correction",
        ))

        # Save to learned rules so this description auto-matches next time
        account = txn.account
        institution = account.institution if account else self._institution
        LearnedPatternCategorizer(self._session).save_correction(
            description=txn.description,
            institution=institution,
            category_id=category_id,
            category_name=new_category_name,
        )

        self._session.flush()

    def _load_category_names(self) -> list[str]:
        rows = self._session.execute(select(Category.name)).scalars().all()
        return list(rows)

    def _load_category_id_map(self) -> dict[str, int]:
        rows = self._session.execute(select(Category.name, Category.id)).all()
        return {name: id_ for name, id_ in rows}
