import logging
from finance_tracker.services.categorisation.base import BaseCategorizer, CategoryResult
from finance_tracker.services.categorisation.rules import get_rules_for

logger = logging.getLogger(__name__)


class RuleBasedCategorizer(BaseCategorizer):
    """
    Layer 1 — fast pattern matching using bank-specific rule lists.
    Rules are defined in services/categorisation/rules/{bank}_rules.py.
    Returns None if no rule matches, signalling the pipeline to try Layer 2.
    """

    def categorize(
        self,
        description: str,
        institution: str,
        dr_cr: str,
    ) -> CategoryResult | None:
        rules = get_rules_for(institution)
        for rule in rules:
            if rule.matches(description, dr_cr):
                logger.debug(
                    "Rule match: %r → %r (pattern: %r)",
                    description, rule.category, rule.pattern,
                )
                return CategoryResult(
                    category_name=rule.category,
                    confidence="high",
                    source="rule",
                    matched=True,
                )
        return None
