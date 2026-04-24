"""
Tests for the three-layer categorisation pipeline.
Uses an in-memory SQLite DB with seeded categories.
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.database import Base
from finance_tracker.models import Account, AccountType, Transaction, DrCr
from finance_tracker.models.transaction import Category
from finance_tracker.models.categorisation import CategorizationLog, LearnedRule
from finance_tracker.services.categorisation.pipeline import CategorizationPipeline
from finance_tracker.services.categorisation.rule_categorizer import RuleBasedCategorizer
from finance_tracker.services.categorisation.learned_categorizer import LearnedPatternCategorizer
from finance_tracker.services.categorisation.ollama_categorizer import OllamaCategorizer


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragmas(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    sess = Session()

    # Seed categories
    categories = [
        ("Food Delivery", "Food", "expense"),
        ("Groceries", "Food", "expense"),
        ("Dining Out", "Food", "expense"),
        ("Salary", "Income", "income"),
        ("Interest", "Income", "income"),
        ("Mutual Fund SIP", "Investments", "investment"),
        ("Credit Card Payment", "Finance", "transfer"),
        ("Insurance Premium", "Finance", "expense"),
        ("Uncategorised", None, "expense"),
        ("UPI Transfer", "Transfers", "transfer"),
        ("Other Income", "Income", "income"),
        ("Dividends", "Income", "income"),
        ("Account Transfer", "Transfers", "transfer"),
    ]
    for name, parent, txn_type in categories:
        sess.add(Category(name=name, parent_name=parent, txn_type=txn_type))

    # Seed account
    acct = Account(
        name="ICICI Savings",
        account_type=AccountType.SAVINGS,
        institution="ICICI Bank",
        currency="INR",
    )
    sess.add(acct)
    sess.commit()

    yield sess
    sess.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def icici_account(session):
    return session.query(Account).filter_by(institution="ICICI Bank").first()


def make_txn(session, account_id, description, dr_cr="DR", amount="100.00"):
    txn = Transaction(
        account_id=account_id,
        txn_date=date(2026, 3, 1),
        amount=Decimal(amount),
        dr_cr=dr_cr,
        description=description,
        category="Uncategorised",
    )
    session.add(txn)
    session.flush()
    return txn


# ── Rule categorizer ──────────────────────────────────────────────────────────

def test_rule_matches_swiggy():
    cat = RuleBasedCategorizer()
    result = cat.categorize("UPI / Swiggy / food delivery", "ICICI Bank", "DR")
    assert result is not None
    assert result.category_name == "Food Delivery"
    assert result.source == "rule"
    assert result.confidence == "high"


def test_rule_matches_salary_credit():
    cat = RuleBasedCategorizer()
    result = cat.categorize("Salary credit for March", "ICICI Bank", "CR")
    assert result is not None
    assert result.category_name == "Salary"


def test_rule_no_match_returns_none():
    cat = RuleBasedCategorizer()
    result = cat.categorize("Some totally unknown merchant XYZ", "ICICI Bank", "DR")
    assert result is None


def test_rule_dr_cr_direction_filter():
    cat = RuleBasedCategorizer()
    # Salary rule only matches CR
    result = cat.categorize("salary payment", "ICICI Bank", "DR")
    assert result is None


def test_rule_no_rules_for_unknown_bank():
    cat = RuleBasedCategorizer()
    result = cat.categorize("UPI / Swiggy / food", "Unknown Bank XYZ", "DR")
    assert result is None


def test_rule_matches_mutual_fund():
    cat = RuleBasedCategorizer()
    result = cat.categorize("ACH / Indian Clearing Corp / SIP", "ICICI Bank", "DR")
    assert result is not None
    assert result.category_name == "Mutual Fund SIP"


def test_rule_matches_cred():
    cat = RuleBasedCategorizer()
    result = cat.categorize("UPI / Cred Club / payment on AXIS BANK", "ICICI Bank", "DR")
    assert result is not None
    assert result.category_name == "Credit Card Payment"


# ── Learned categorizer ───────────────────────────────────────────────────────

def test_learned_save_and_retrieve(session, icici_account):
    learner = LearnedPatternCategorizer(session)

    learner.save_correction(
        description="UPI / Some New Merchant / gift",
        institution="ICICI Bank",
        category_id=1,
        category_name="Groceries",
    )
    session.commit()

    result = learner.categorize(
        "UPI / Some New Merchant / gift",
        "ICICI Bank",
        "DR",
    )
    assert result is not None
    assert result.category_name == "Groceries"
    assert result.source == "learned"


def test_learned_no_match_returns_none(session):
    learner = LearnedPatternCategorizer(session)
    result = learner.categorize("Description never seen before XYZ", "ICICI Bank", "DR")
    assert result is None


def test_learned_institution_scoped(session):
    learner = LearnedPatternCategorizer(session)
    # Saved under ICICI Bank — should NOT match YES Bank
    learner.save_correction(
        description="some vendor abc",
        institution="ICICI Bank",
        category_id=1,
        category_name="Dining Out",
    )
    session.commit()

    result = learner.categorize("some vendor abc", "YES Bank", "DR")
    assert result is None


def test_learned_upsert_updates_count(session):
    learner = LearnedPatternCategorizer(session)
    desc = "repeat merchant test"

    learner.save_correction(desc, "ICICI Bank", 1, "Groceries")
    session.commit()
    learner.save_correction(desc, "ICICI Bank", 1, "Groceries")
    session.commit()

    from sqlalchemy import select
    rule = session.execute(
        select(LearnedRule).where(
            LearnedRule.institution == "ICICI Bank",
            LearnedRule.description_pattern == desc.lower(),
        )
    ).scalar_one_or_none()
    assert rule is not None
    assert rule.match_count >= 2


# ── Ollama categorizer ────────────────────────────────────────────────────────

def test_ollama_gracefully_unavailable():
    """Ollama not running — should return None without crashing."""
    ollama = OllamaCategorizer(valid_categories=["Food Delivery", "Groceries"])
    result = ollama.categorize("UPI / Swiggy / food", "ICICI Bank", "DR")
    assert result is None


# ── Full pipeline ─────────────────────────────────────────────────────────────

def test_pipeline_categorises_on_run(session, icici_account):
    txn = make_txn(session, icici_account.id, "UPI / Swiggy / dinner")
    pipeline = CategorizationPipeline(session, "ICICI Bank")
    summary = pipeline.run([txn])

    assert txn.category == "Food Delivery"
    assert summary.get("rule", 0) >= 1


def test_pipeline_writes_log(session, icici_account):
    txn = make_txn(session, icici_account.id, "ACH / Indian Clearing Corp / sip")
    pipeline = CategorizationPipeline(session, "ICICI Bank")
    pipeline.run([txn])

    from sqlalchemy import select
    log = session.execute(
        select(CategorizationLog).where(
            CategorizationLog.transaction_id == txn.id
        )
    ).scalar_one_or_none()

    assert log is not None
    assert log.source == "rule"
    assert log.category_name == "Mutual Fund SIP"


def test_pipeline_skips_already_categorised(session, icici_account):
    txn = make_txn(session, icici_account.id, "UPI / Swiggy / breakfast")
    txn.category = "Dining Out"  # pre-categorised
    session.flush()

    pipeline = CategorizationPipeline(session, "ICICI Bank")
    pipeline.run([txn])

    assert txn.category == "Dining Out"  # must not be overwritten


def test_pipeline_manual_correction_saves_learned(session, icici_account):
    txn = make_txn(session, icici_account.id, "UPI / Mystery Shop / unknown")
    session.flush()

    pipeline = CategorizationPipeline(session, "ICICI Bank")
    pipeline.run([txn])

    # Manually correct
    pipeline.apply_manual_correction(txn.id, "Groceries")
    session.commit()

    assert txn.category == "Groceries"

    # Verify learned rule was saved
    from sqlalchemy import select
    rule = session.execute(
        select(LearnedRule).where(
            LearnedRule.description_pattern == "upi / mystery shop / unknown"
        )
    ).scalar_one_or_none()
    assert rule is not None
    assert rule.category_name == "Groceries"


def test_pipeline_invalid_category_rejected(session, icici_account):
    txn = make_txn(session, icici_account.id, "UPI / Swiggy / lunch")
    pipeline = CategorizationPipeline(session, "ICICI Bank")
    with pytest.raises(ValueError, match="not in master table"):
        pipeline.apply_manual_correction(txn.id, "Nonexistent Category XYZ")
