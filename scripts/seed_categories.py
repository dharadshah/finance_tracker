"""
Seed script: populates the categories table with a default set.
Safe to run multiple times — skips categories that already exist.

Run with:
    python scripts/seed_categories.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from finance_tracker.database import get_session, init_db
from finance_tracker.models.transaction import Category

DEFAULT_CATEGORIES = [
    # (name, parent_name, txn_type)

    # Income
    ("Salary", "Income", "income"),
    ("Freelance", "Income", "income"),
    ("Interest", "Income", "income"),
    ("Dividends", "Income", "income"),
    ("Rental Income", "Income", "income"),
    ("Other Income", "Income", "income"),

    # Food
    ("Groceries", "Food", "expense"),
    ("Dining Out", "Food", "expense"),
    ("Food Delivery", "Food", "expense"),
    ("Cafe / Coffee", "Food", "expense"),

    # Transport
    ("Fuel", "Transport", "expense"),
    ("Auto / Rickshaw", "Transport", "expense"),
    ("Cab / Ola / Uber", "Transport", "expense"),
    ("Public Transport", "Transport", "expense"),
    ("Vehicle Maintenance", "Transport", "expense"),
    ("Parking / Tolls", "Transport", "expense"),

    # Housing
    ("Rent", "Housing", "expense"),
    ("Maintenance / Society", "Housing", "expense"),
    ("Electricity", "Housing", "expense"),
    ("Water", "Housing", "expense"),
    ("Internet / Broadband", "Housing", "expense"),
    ("Home Supplies", "Housing", "expense"),
    ("Maid Salary", "Housing", "expense"),


    # Health
    ("Doctor / Consultation", "Health", "expense"),
    ("Medicines", "Health", "expense"),
    ("Lab Tests", "Health", "expense"),
    ("Health Insurance", "Health", "expense"),
    ("Gym / Fitness", "Health", "expense"),

    # Shopping
    ("Clothing", "Shopping", "expense"),
    ("Electronics", "Shopping", "expense"),
    ("Amazon / Flipkart", "Shopping", "expense"),
    ("Personal Care", "Shopping", "expense"),
    ("UPI Wallet", "Shopping", "expense"),

    # Entertainment
    ("OTT Subscriptions", "Entertainment", "expense"),
    ("Movies / Events", "Entertainment", "expense"),
    ("Books / Courses", "Entertainment", "expense"),
    ("Games", "Entertainment", "expense"),

    # Finance
    ("Credit Card Payment", "Finance", "transfer"),
    ("Reward Points", "Income", "income"),
    ("Loan EMI", "Finance", "expense"),
    ("Insurance Premium", "Finance", "expense"),
    ("Bank Charges", "Finance", "expense"),
    ("Tax Payment", "Finance", "expense"),

    # Investments
    ("Mutual Fund SIP", "Investments", "investment"),
    ("Mutual Fund Lumpsum", "Investments", "investment"),
    ("Stock Purchase", "Investments", "investment"),
    ("PPF / EPF", "Investments", "investment"),
    ("FD / RD", "Investments", "investment"),
    ("NPS", "Investments", "investment"),

    # Transfers
    ("Account Transfer", "Transfers", "transfer"),
    ("Family / Gift", "Transfers", "transfer"),
    ("UPI Transfer", "Transfers", "transfer"),

    # Uncategorised
    ("Uncategorised", None, "expense"),
]


def seed():
    init_db()
    added = 0
    skipped = 0

    with get_session() as session:
        existing = {c.name for c in session.query(Category).all()}

        for name, parent_name, txn_type in DEFAULT_CATEGORIES:
            if name in existing:
                skipped += 1
                continue
            session.add(Category(name=name, parent_name=parent_name, txn_type=txn_type))
            added += 1

    print(f"Categories seeded: {added} added, {skipped} already existed.")


if __name__ == "__main__":
    seed()
