from finance_tracker.services.categorisation.rules.base_rules import Rule
from finance_tracker.services.categorisation.rules.icici_rules import ICICI_RULES

# Maps institution name → rule list.
# Adding a new bank: create its rules file and add one entry here.
INSTITUTION_RULES: dict[str, list[Rule]] = {
    "ICICI Bank": ICICI_RULES,
    # "YES Bank":   YES_BANK_RULES,
    # "Axis Bank":  AXIS_BANK_RULES,
    # "HDFC Bank":  HDFC_BANK_RULES,
}


def get_rules_for(institution: str) -> list[Rule]:
    return INSTITUTION_RULES.get(institution, [])
