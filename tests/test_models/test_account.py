"""
Unit tests for Account and related models.
Uses an in-memory SQLite DB — no file created, no cleanup needed.
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.database import Base
from finance_tracker.models import (
    Account, AccountType,
    Transaction, DrCr,
    CreditCardDue, DueStatus,
    MFHolding, StockHolding,
    NetWorthSnapshot,
)


@pytest.fixture(scope="module")
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragmas(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    sess = Session()
    yield sess
    sess.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def savings_account(session):
    acct = Account(
        name="HDFC Savings",
        account_type=AccountType.SAVINGS,
        institution="HDFC Bank",
        currency="INR",
    )
    session.add(acct)
    session.commit()
    return acct


def test_account_creation(savings_account):
    assert savings_account.id is not None
    assert savings_account.name == "HDFC Savings"
    assert savings_account.account_type == AccountType.SAVINGS
    assert savings_account.is_active is True
    assert savings_account.currency == "INR"


def test_transaction_signed_amount(session, savings_account):
    txn = Transaction(
        account_id=savings_account.id,
        txn_date=date(2025, 1, 15),
        amount=Decimal("1500.00"),
        dr_cr=DrCr.DEBIT,
        description="Swiggy order",
    )
    session.add(txn)
    session.commit()

    assert txn.signed_amount == Decimal("-1500.00")

    txn_cr = Transaction(
        account_id=savings_account.id,
        txn_date=date(2025, 1, 25),
        amount=Decimal("50000.00"),
        dr_cr=DrCr.CREDIT,
        description="Salary credit",
    )
    session.add(txn_cr)
    session.commit()

    assert txn_cr.signed_amount == Decimal("50000.00")


def test_credit_card_outstanding(session):
    cc_acct = Account(
        name="HDFC Regalia",
        account_type=AccountType.CREDIT_CARD,
        institution="HDFC Bank",
        currency="INR",
    )
    session.add(cc_acct)
    session.commit()

    due = CreditCardDue(
        account_id=cc_acct.id,
        statement_date=date(2025, 1, 1),
        due_date=date(2025, 1, 20),
        total_due=Decimal("12000.00"),
        minimum_due=Decimal("600.00"),
        amount_paid=Decimal("5000.00"),
        status=DueStatus.PAID_PARTIAL,
    )
    session.add(due)
    session.commit()

    assert due.outstanding == Decimal("7000.00")


def test_mf_holding_cost_value(session, savings_account):
    mf = MFHolding(
        account_id=savings_account.id,
        scheme_code="119598",
        scheme_name="Parag Parikh Flexi Cap Fund",
        folio_number="12345678",
        units=Decimal("100.0000"),
        avg_nav=Decimal("72.5000"),
        last_updated=date(2025, 1, 31),
    )
    session.add(mf)
    session.commit()

    assert mf.cost_value == Decimal("7250.0000")


def test_stock_holding_invested_value(session, savings_account):
    stock = StockHolding(
        account_id=savings_account.id,
        symbol="RELIANCE",
        exchange="NSE",
        quantity=Decimal("10.0000"),
        avg_buy_price=Decimal("2450.0000"),
        last_updated=date(2025, 1, 31),
    )
    session.add(stock)
    session.commit()

    assert stock.invested_value == Decimal("24500.0000")


def test_net_worth_snapshot(session):
    snap = NetWorthSnapshot(
        snapshot_date=date(2025, 1, 31),
        total_assets=Decimal("1500000.00"),
        total_liabilities=Decimal("200000.00"),
        net_worth=Decimal("1300000.00"),
    )
    session.add(snap)
    session.commit()

    assert snap.id is not None
    assert snap.net_worth == Decimal("1300000.00")


def test_seed_idempotency():
    """Seed script must not raise if called twice."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from scripts.seed_categories import seed
    seed()
    seed()
