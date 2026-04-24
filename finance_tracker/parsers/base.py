from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass
class ParsedTransaction:
    """
    Normalised transaction record produced by any parser.
    Parser output is always this shape — the repository layer
    does not need to know which parser produced it.
    """
    txn_date: date
    amount: Decimal
    dr_cr: str                      # 'DR' or 'CR'
    description: str                # cleaned, no transaction IDs
    raw_description: str            # original text from source file
    reference_number: str | None = None
    mode: str | None = None         # UPI / NEFT / ACH / IMPS etc.
    balance: Decimal | None = None
    source_file: str | None = None


@dataclass
class ParseResult:
    """
    Full result returned by a parser after processing one file.
    Contains transactions plus metadata extracted from the file.
    """
    transactions: list[ParsedTransaction] = field(default_factory=list)
    account_number_masked: str | None = None   # e.g. XXXXXXXX6760
    account_holder_name: str | None = None
    institution: str | None = None
    statement_period_start: date | None = None
    statement_period_end: date | None = None
    currency: str = "INR"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class BaseStatementParser(ABC):
    """
    Abstract base class for all statement parsers.

    Design principles:
    - One subclass per institution/format (Open/Closed)
    - Subclasses implement parse() only — sanitisation is handled here
    - Personal data (name, address, full account numbers) is stripped
      before any data leaves the parser

    To add a new bank: subclass this, implement parse(), done.
    """

    # Subclasses declare which institution they handle
    INSTITUTION: str = ""

    def process(self, file_path: str | Path) -> ParseResult:
        """
        Public entry point. Calls parse() then sanitises the result.
        Always call this — never call parse() directly.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Statement file not found: {path}")

        result = self.parse(path)

        for txn in result.transactions:
            txn.source_file = path.name  # filename only, never full path
            txn.description = self._clean_description(txn.raw_description)

        result = self._sanitise(result)
        return result

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """
        Parse the file and return a ParseResult.
        Subclasses implement this method only.
        raw_description should be set to the original text.
        description will be overwritten by process() after cleaning.
        """
        ...

    def _clean_description(self, raw: str) -> str:
        """
        Strips UPI transaction IDs, reference hashes, and other noise
        from description strings. Subclasses may override for custom logic.

        ICICI UPI format:
        UPI/VENDOR NAME/upihandle@bank/memo/BANK NAME/txnid/hash/
        We keep: UPI / VENDOR NAME / memo
        """
        import re

        desc = raw.strip().rstrip("/")

        # UPI transactions — extract vendor and memo
        upi_match = re.match(
            r"UPI/([^/]+)/[^/]+/([^/]+)/[^/]+/\d{6,}/\w+",
            desc,
            re.IGNORECASE,
        )
        if upi_match:
            vendor = upi_match.group(1).strip().title()
            memo = upi_match.group(2).strip()
            if memo.upper() in ("UPI", "PAY VIA RAZORPAY", "MANDATEEXE", "PAY VIA RAZO"):
                return f"UPI / {vendor}"
            return f"UPI / {vendor} / {memo}"

        # UPL (UPI collect / pull) — strip reference
        upl_match = re.match(r"UPL/\d+/(\w+)/.*", desc, re.IGNORECASE)
        if upl_match:
            return f"UPI Collect / {upl_match.group(1)}"

        # IMPS transfers
        imps_match = re.match(
            r"MMT/IMPS/\d+/(?:IMPS/)?([^/]+)/", desc, re.IGNORECASE
        )
        if imps_match:
            return f"IMPS / {imps_match.group(1).strip().title()}"

        # ACH payments — keep the payee name
        ach_match = re.match(r"ACH/([^/]+)/", desc, re.IGNORECASE)
        if ach_match:
            return f"ACH / {ach_match.group(1).strip().title()}"

        # NEFT
        neft_match = re.match(r"NEFT-\w+-([^-]+)-", desc, re.IGNORECASE)
        if neft_match:
            return f"NEFT / {neft_match.group(1).strip().title()}"

        # INF/INFT (internet fund transfer)
        inft_match = re.match(r"INF/INFT/\d+/(.+)", desc, re.IGNORECASE)
        if inft_match:
            return f"Fund Transfer / {inft_match.group(1).strip().title()}"

        # IIN/I-Debit (internet debit)
        idebit_match = re.match(r"IIN/I-Debit/([^/]+)/", desc, re.IGNORECASE)
        if idebit_match:
            return f"Direct Debit / {idebit_match.group(1).strip().title()}"

        # CAM/cash withdrawal
        cam_match = re.match(r"CAM/\w+/CASH WDL/(.+)", desc, re.IGNORECASE)
        if cam_match:
            return f"Cash Withdrawal / {cam_match.group(1).strip()}"

        # Sweep entries from linked FD
        sweep_match = re.match(r"(\d+): (.+)", desc)
        if sweep_match:
            return f"FD Sweep / {sweep_match.group(2).strip().title()}"

        # Interest credit
        if "Int.Pd" in desc or "Interest" in desc.title():
            return "Interest Credit"

        return desc

    def _sanitise(self, result: ParseResult) -> ParseResult:
        """
        Removes personal data that must not be stored in the database.
        - Account holder name is cleared after use
        - Full account numbers are never stored (masked form is kept)
        - Address lines are never extracted
        """
        result.account_holder_name = None
        return result

    @staticmethod
    def _to_decimal(value: str) -> Decimal:
        cleaned = value.replace(",", "").strip()
        if not cleaned or cleaned == "0":
            return Decimal("0")
        return Decimal(cleaned)
