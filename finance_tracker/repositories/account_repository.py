import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from finance_tracker.models import Account, AccountType

logger = logging.getLogger(__name__)


class AccountRepository:
    """
    All database reads and writes for accounts.
    """

    def __init__(self, session: Session):
        self._session = session

    def get_all(self, include_inactive: bool = False) -> list[Account]:
        stmt = select(Account)
        if not include_inactive:
            stmt = stmt.where(Account.is_active == True)  # noqa: E712
        stmt = stmt.order_by(Account.institution, Account.name)
        return list(self._session.execute(stmt).scalars())

    def get_by_id(self, account_id: int) -> Account | None:
        return self._session.get(Account, account_id)

    def get_by_institution_and_type(
        self, institution: str, account_type: AccountType
    ) -> list[Account]:
        stmt = select(Account).where(
            Account.institution == institution,
            Account.account_type == account_type,
        )
        return list(self._session.execute(stmt).scalars())

    def find_by_masked_number(self, masked_number: str) -> Account | None:
        """
        Finds an account by its masked account number stored in notes.
        Used during import to auto-match a statement to an account.
        """
        stmt = select(Account).where(Account.notes.contains(masked_number))
        return self._session.execute(stmt).scalar_one_or_none()

    def create(
        self,
        name: str,
        account_type: AccountType,
        institution: str,
        masked_number: str | None = None,
        is_active: bool = True,
        notes: str | None = None,
    ) -> Account:
        acct = Account(
            name=name,
            account_type=account_type,
            institution=institution,
            is_active=is_active,
            notes=notes or masked_number,
        )
        self._session.add(acct)
        self._session.flush()
        logger.info("Created account: %s (%s)", name, institution)
        return acct
