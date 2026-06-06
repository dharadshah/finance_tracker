import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from finance_tracker.services.categorisation.base import BaseCategorizer, CategoryResult
from finance_tracker.models.categorisation import LearnedRule

logger = logging.getLogger(__name__)


class LearnedPatternCategorizer(BaseCategorizer):
    """
    Layer 2 — uses descriptions corrected manually by the user.
    Loads ALL rules for the institution into memory once,
    then does fast dict lookups instead of per-transaction DB queries.
    """

    def __init__(self, session: Session):
        self._session = session
        self._cache: dict[tuple[str, str], LearnedRule] = {}
        self._loaded_institution: str | None = None

    def _ensure_loaded(self, institution: str) -> None:
        """Load all rules for this institution into memory if not already loaded."""
        if self._loaded_institution == institution:
            return
        rules = self._session.execute(
            select(LearnedRule).where(LearnedRule.institution == institution)
        ).scalars().all()
        self._cache = {
            (institution, r.description_pattern): r
            for r in rules
        }
        self._loaded_institution = institution
        logger.debug("Loaded %d learned rules for %s", len(rules), institution)

    def categorize(
        self,
        description: str,
        institution: str,
        dr_cr: str,
    ) -> CategoryResult | None:
        self._ensure_loaded(institution)
        key = (institution, description.lower().strip())
        rule = self._cache.get(key)
        if rule is None:
            return None
        logger.debug(
            "Learned match: %r -> %r (seen %d times)",
            description, rule.category_name, rule.match_count,
        )
        return CategoryResult(
            category_name=rule.category_name,
            confidence="high",
            source="learned",
            matched=True,
        )

    def save_correction(
        self,
        description: str,
        institution: str,
        category_id: int,
        category_name: str,
    ) -> None:
        """
        Called when a user manually corrects a category.
        Upserts into learned_rules so this description is auto-matched next time.
        """
        from datetime import datetime, timezone

        key = description.lower().strip()
        stmt = select(LearnedRule).where(
            and_(
                LearnedRule.institution == institution,
                LearnedRule.description_pattern == key,
            )
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        if existing:
            existing.category_id = category_id
            existing.category_name = category_name
            existing.match_count += 1
            existing.last_seen_at = datetime.now(timezone.utc)
        else:
            self._session.add(LearnedRule(
                institution=institution,
                description_pattern=key,
                category_id=category_id,
                category_name=category_name,
            ))

        # Invalidate cache so next import picks up the new rule
        self._loaded_institution = None

        logger.info(
            "Learned rule saved: institution=%r %r -> %r",
            institution, key, category_name,
        )