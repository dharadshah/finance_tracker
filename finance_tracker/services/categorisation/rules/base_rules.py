from dataclasses import dataclass
import re


@dataclass
class Rule:
    """
    A single pattern → category mapping.
    pattern: regex applied to the cleaned description (case-insensitive)
    category: must match a name in the categories master table
    dr_cr: 'DR', 'CR', or None (matches either direction)
    """
    pattern: str
    category: str
    dr_cr: str | None = None

    def matches(self, description: str, dr_cr: str) -> bool:
        if self.dr_cr and self.dr_cr != dr_cr:
            return False
        return bool(re.search(self.pattern, description, re.IGNORECASE))
