"""
Seed script: populates learned_rules with known categorisation mappings.
Safe to run multiple times — skips rules that already exist.

Run with:
    poetry run python scripts/seed_rules.py
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from finance_tracker.database import get_session, init_db
from finance_tracker.models.categorisation import LearnedRule
from finance_tracker.models.transaction import Category

# (institution, description_pattern, category_name)
DEFAULT_RULES = [
    ("ICICI Bank", "UPI Wallet",                      "UPI Wallet"),
    ("ICICI Bank", "Salary / Sonalben D",             "Maid Salary"),
    ("ICICI Bank", "UPI / Bseindia C / Pay Via Ra",   "Mutual Fund Lumpsum"),
    ("ICICI Bank", "Fund Transfer / Jisha Shah",       "Account Transfer"),
]


def seed():
    init_db()
    added = 0
    skipped = 0

    with get_session() as session:
        existing = {
            (r.institution, r.description_pattern)
            for r in session.query(LearnedRule).all()
        }
        categories = {c.name: c for c in session.query(Category).all()}

        for institution, pattern, category_name in DEFAULT_RULES:
            if (institution, pattern) in existing:
                skipped += 1
                continue

            cat = categories.get(category_name)
            if cat is None:
                print(f"WARNING: Category not found, skipping rule: {category_name!r}")
                skipped += 1
                continue

            session.add(LearnedRule(
                institution=institution,
                description_pattern=pattern,
                category_id=cat.id,
                category_name=cat.name,
                match_count=1,
                last_seen_at=datetime.now(timezone.utc),
            ))
            added += 1

    print(f"Rules seeded: {added} added, {skipped} already existed.")


if __name__ == "__main__":
    seed()