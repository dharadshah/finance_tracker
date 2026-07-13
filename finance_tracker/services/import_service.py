import logging
from dataclasses import dataclass, field
from pathlib import Path

from finance_tracker.database import get_session
from finance_tracker.models import AccountType
from finance_tracker.parsers import get_parser, ParseResult
from finance_tracker.repositories.account_repository import AccountRepository
from finance_tracker.repositories.transaction_repository import TransactionRepository
from finance_tracker.services.categorisation import CategorizationPipeline
from finance_tracker.models import AccountType
from finance_tracker.repositories.mf_transaction_repository import MFTransactionRepository

logger = logging.getLogger(__name__)


@dataclass
class ImportSummary:
    """Result returned to the UI after an import run."""
    account_name: str
    institution: str
    account_number_masked: str | None
    statement_period: str
    transactions_inserted: int
    transactions_skipped: int
    categorisation_summary: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_processed(self) -> int:
        return self.transactions_inserted + self.transactions_skipped

@dataclass
class MFImportSummary:
    """Result returned to the UI after an NJ India MF import run."""
    account_name:        str
    institution:         str
    statement_period:    str
    transactions_inserted: int
    transactions_skipped:  int
    warnings: list[str] = field(default_factory=list)
    errors:   list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_processed(self) -> int:
        return self.transactions_inserted + self.transactions_skipped

class ImportService:
    """
    Orchestrates the full import pipeline:
    1. Parse the file
    2. Resolve or create the account
    3. Save transactions (skip duplicates)
    4. Run categorisation pipeline on new transactions
    5. Return summary for the UI
    """

    def import_statement(
        self,
        file_path: str | Path,
        parser_key: str,
        account_id: int | None = None,
    ) -> ImportSummary:
        path = Path(file_path)
        parser = get_parser(parser_key)

        logger.info("Parsing %s with %s", path.name, parser.__class__.__name__)
        result: ParseResult = parser.process(path)

        if result.has_errors:
            return ImportSummary(
                account_name="",
                institution=parser.INSTITUTION,
                account_number_masked=result.account_number_masked,
                statement_period="",
                transactions_inserted=0,
                transactions_skipped=0,
                warnings=result.warnings,
                errors=result.errors,
            )

        cat_summary = {}

        with get_session() as session:
            acct_repo = AccountRepository(session)
            txn_repo = TransactionRepository(session)

            account = self._resolve_account(
                acct_repo, result, parser.INSTITUTION, account_id
            )

            inserted, skipped, new_txns = txn_repo.save_parsed_transactions(
                result.transactions, account.id
            )

            # Run categorisation on newly inserted transactions only
            if inserted > 0 and new_txns:
                pipeline = CategorizationPipeline(
                    session=session,
                    institution=parser.INSTITUTION,
                )
                cat_summary = pipeline.run(new_txns)

            # Save closing balance to account
            if result.closing_balance is not None:
                account.current_balance = result.closing_balance
                session.flush()
                
        period = ""
        if result.statement_period_start and result.statement_period_end:
            period = (
                f"{result.statement_period_start.strftime('%d %b %Y')} – "
                f"{result.statement_period_end.strftime('%d %b %Y')}"
            )

        return ImportSummary(
            account_name=account.name,
            institution=parser.INSTITUTION,
            account_number_masked=result.account_number_masked,
            statement_period=period,
            transactions_inserted=inserted,
            transactions_skipped=skipped,
            categorisation_summary=cat_summary,
            warnings=result.warnings,
            errors=result.errors,
        )

    def _resolve_account(self, repo, result, institution, account_id):
        if account_id is not None:
            acct = repo.get_by_id(account_id)
            if acct is None:
                raise ValueError(f"Account ID {account_id} not found.")
            return acct

        if result.account_number_masked:
            acct = repo.find_by_masked_number(result.account_number_masked)
            if acct:
                return acct

        name = self._generate_account_name(institution, result.account_number_masked)
        return repo.create(
            name=name,
            account_type=AccountType.SAVINGS,
            institution=institution,
            masked_number=result.account_number_masked,
            is_active=True,
        )

    @staticmethod
    def _generate_account_name(institution: str, masked: str | None) -> str:
        if masked:
            last4 = masked[-4:] if len(masked) >= 4 else masked
            return f"{institution} ...{last4}"
        return institution

    def import_mf_transactions(
        self,
        file_path: str | Path,
        parser_key: str,
        account_id: int | None = None,
    ) -> MFImportSummary:
        """
        Import pipeline for MF transaction reports (NJ India).
        Parses the file, resolves or creates the account, saves
        ParsedMFTransaction records. No categorisation is run.
        """
        path = Path(file_path)
        parser = get_parser(parser_key)

        logger.info("Parsing MF file %s with %s", path.name, parser.__class__.__name__)
        result: ParseResult = parser.process(path)

        if result.has_errors:
            return MFImportSummary(
                account_name="",
                institution=parser.INSTITUTION,
                statement_period="",
                transactions_inserted=0,
                transactions_skipped=0,
                warnings=result.warnings,
                errors=result.errors,
            )

        with get_session() as session:
            acct_repo   = AccountRepository(session)
            mf_txn_repo = MFTransactionRepository(session)

            account = self._resolve_mf_account(
                acct_repo, parser.INSTITUTION, account_id
            )

            inserted, skipped = mf_txn_repo.save_parsed_mf_transactions(
                result.mf_transactions, account.id
            )

        period = ""
        if result.statement_period_start and result.statement_period_end:
            period = (
                f"{result.statement_period_start.strftime('%d %b %Y')} - "
                f"{result.statement_period_end.strftime('%d %b %Y')}"
            )

        return MFImportSummary(
            account_name=parser.INSTITUTION,
            institution=parser.INSTITUTION,
            statement_period=period,
            transactions_inserted=inserted,
            transactions_skipped=skipped,
            warnings=result.warnings,
            errors=result.errors,
        )

    def _resolve_mf_account(
        self,
        repo: AccountRepository,
        institution: str,
        account_id: int | None,
    ) -> object:
        """
        Resolves the MF account for NJ India.
        If account_id is supplied, uses that.
        Otherwise finds or creates an account by institution name.
        """
        if account_id is not None:
            acct = repo.get_by_id(account_id)
            if acct is None:
                raise ValueError(f"Account ID {account_id} not found.")
            return acct

        existing = repo.get_by_institution_and_type(
            institution, AccountType.MF_FOLIO
        )
        if existing:
            return existing[0]

        return repo.create(
            name=institution,
            account_type=AccountType.MF_FOLIO,
            institution=institution,
            is_active=True,
        )