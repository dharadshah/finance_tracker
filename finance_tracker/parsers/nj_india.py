"""
NJ India Invest transaction report parser.

Supports the XLS-format Detail Transaction Report exported from the
NJ India Invest portal. Handles both Inflow and Outflow sections,
filters out Failed transactions, and produces ParsedMFTransaction objects.

File format: legacy .xls  (requires xlrd engine).
"""

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from finance_tracker.parsers.base import (
    BaseStatementParser,
    ParseResult,
    ParsedMFTransaction,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INSTITUTION    = "NJ India Invest"
_DATE_FMT       = "%d-%m-%Y"

_INFLOW_MARKER  = "Inflow"
_OUTFLOW_MARKER = "Outflow"
_SR_NO_HEADER   = "Sr. No."
_STATUS_FAILED  = "failed"

_DIRECTION_INFLOW  = "inflow"
_DIRECTION_OUTFLOW = "outflow"

# Column names after lower-stripping
_COL_SR_NO      = "sr. no."
_COL_TXN_DATE   = "transaction date"
_COL_SCHEME     = "scheme"
_COL_FOLIO      = "folio no"
_COL_TXN_TYPE   = "transaction type"
_COL_UNITS      = "units"
_COL_AMOUNT     = "amount"
_COL_NET_AMOUNT = "net amount"
_COL_STATUS     = "transaction status"


class NJIndiaParser(BaseStatementParser):
    """
    Parser for NJ India Invest Detail Transaction Report (.xls).

    The report contains two independent sections (Inflow / Outflow),
    each with its own column header row. Section boundaries are detected
    dynamically — fixed row numbers are not assumed.

    Output goes into ParseResult.mf_transactions (not .transactions).
    One parser instance per file.
    """

    INSTITUTION = _INSTITUTION

    def parse(self, file_path: Path) -> ParseResult:
        result = ParseResult(institution=self.INSTITUTION)

        try:
            raw_df = pd.read_excel(
                file_path,
                engine="xlrd",
                header=None,
                dtype=str,
            )
        except Exception as exc:
            result.errors.append(f"Could not read file: {exc}")
            return result

        self._extract_metadata(raw_df, result)
        self._parse_sections(raw_df, file_path.name, result)

        logger.info(
            "NJIndiaParser: %d transactions from %s",
            len(result.mf_transactions),
            file_path.name,
        )
        return result

    # ------------------------------------------------------------------
    # Private — metadata
    # ------------------------------------------------------------------

    def _extract_metadata(self, df: pd.DataFrame, result: ParseResult) -> None:
        """
        Extracts investor name and date range from report header rows.
        Row 1 format: 'From: DD-MM-YYYY To:DD-MM-YYYY   Investors : Name'
        """
        try:
            header = str(df.iloc[1, 0])
            if "Investors :" in header:
                result.account_holder_name = header.split("Investors :")[-1].strip()
            if "From:" in header and "To:" in header:
                parts = header.split()
                for i, part in enumerate(parts):
                    if part == "From:":
                        result.statement_period_start = datetime.strptime(
                            parts[i + 1], _DATE_FMT
                        ).date()
                    if part.startswith("To:"):
                        raw = part.replace("To:", "").strip()
                        if raw:
                            result.statement_period_end = datetime.strptime(
                                raw, _DATE_FMT
                            ).date()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Private — section detection
    # ------------------------------------------------------------------

    def _parse_sections(
        self, df: pd.DataFrame, filename: str, result: ParseResult
    ) -> None:
        """
        Scans rows to locate Inflow and Outflow section header rows,
        then delegates to _parse_section() for each.
        """
        inflow_header_row  = None
        outflow_header_row = None
        current_section    = None

        for idx in range(len(df)):
            first_cell = str(df.iloc[idx, 0]).strip()

            if _INFLOW_MARKER in first_cell and _OUTFLOW_MARKER not in first_cell:
                current_section = _DIRECTION_INFLOW
                continue

            if _OUTFLOW_MARKER in first_cell:
                current_section = _DIRECTION_OUTFLOW
                continue

            if first_cell == _SR_NO_HEADER:
                if current_section == _DIRECTION_INFLOW and inflow_header_row is None:
                    inflow_header_row = idx
                elif current_section == _DIRECTION_OUTFLOW and outflow_header_row is None:
                    outflow_header_row = idx

        if inflow_header_row is not None:
            self._parse_section(
                df, inflow_header_row, _DIRECTION_INFLOW, filename, result
            )

        if outflow_header_row is not None:
            self._parse_section(
                df, outflow_header_row, _DIRECTION_OUTFLOW, filename, result
            )

    def _parse_section(
        self,
        df: pd.DataFrame,
        header_row: int,
        direction: str,
        filename: str,
        result: ParseResult,
    ) -> None:
        """
        Reads one section starting at header_row.
        Stops when Sr. No. is non-numeric (Total row / Notes).
        """
        headers = [
            str(cell).strip().lower() if pd.notna(cell) else ""
            for cell in df.iloc[header_row]
        ]

        for row_idx in range(header_row + 1, len(df)):
            row_dict = dict(zip(headers, df.iloc[row_idx]))

            sr_no = str(row_dict.get(_COL_SR_NO, "")).strip()

            # Stop at Total row, Notes, or blank
            if not sr_no or sr_no.lower() in ("nan", "note:", ""):
                break
            try:
                float(sr_no)
            except ValueError:
                break

            txn = self._build_transaction(
                row_dict, direction, filename, row_idx, result
            )
            if txn is not None:
                result.mf_transactions.append(txn)

    # ------------------------------------------------------------------
    # Private — row parsing
    # ------------------------------------------------------------------

    def _build_transaction(
        self,
        row: dict,
        direction: str,
        filename: str,
        row_idx: int,
        result: ParseResult,
    ) -> ParsedMFTransaction | None:
        """
        Converts one row dict into a ParsedMFTransaction.
        Returns None for Failed rows or rows with unparseable data.
        """
        status = str(row.get(_COL_STATUS, "")).strip().lower()
        if status == _STATUS_FAILED:
            logger.debug("Skipping failed transaction at row %d", row_idx)
            return None

        txn_date = self._parse_date(
            str(row.get(_COL_TXN_DATE, "")).strip(), row_idx, result
        )
        if txn_date is None:
            return None

        # Inflow has Net Amount; Outflow has Amount
        raw_amount = str(
            row.get(_COL_NET_AMOUNT) or row.get(_COL_AMOUNT) or ""
        ).strip()
        amount = self._parse_amount(raw_amount, row_idx, result)
        if amount is None:
            return None

        units = self._parse_units(
            str(row.get(_COL_UNITS, "")).strip(), row_idx, result
        )
        if units is None:
            return None

        scheme_name  = str(row.get(_COL_SCHEME,   "")).strip()
        folio_number = str(row.get(_COL_FOLIO,    "")).strip()
        txn_type     = str(row.get(_COL_TXN_TYPE, "")).strip()

        return ParsedMFTransaction(
            txn_date=txn_date,
            scheme_name=scheme_name,
            folio_number=folio_number,
            txn_type=txn_type,
            direction=direction,
            units=units,
            amount=amount,
            source_file=filename,
        )

    # ------------------------------------------------------------------
    # Private — type coercions
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(
        raw: str, row_idx: int, result: ParseResult
    ) -> date | None:
        try:
            return datetime.strptime(raw, _DATE_FMT).date()
        except ValueError:
            result.errors.append(
                f"Row {row_idx}: unrecognised date '{raw}'"
            )
            return None

    @staticmethod
    def _parse_amount(
        raw: str, row_idx: int, result: ParseResult
    ) -> Decimal | None:
        cleaned = raw.replace(",", "").strip()
        if not cleaned or cleaned == "nan":
            result.errors.append(f"Row {row_idx}: missing amount")
            return None
        try:
            return abs(Decimal(cleaned))
        except InvalidOperation:
            result.errors.append(
                f"Row {row_idx}: could not parse amount '{raw}'"
            )
            return None

    @staticmethod
    def _parse_units(
        raw: str, row_idx: int, result: ParseResult
    ) -> Decimal | None:
        cleaned = raw.replace(",", "").strip()
        if not cleaned or cleaned == "nan":
            result.errors.append(f"Row {row_idx}: missing units")
            return None
        try:
            return abs(Decimal(cleaned))
        except InvalidOperation:
            result.errors.append(
                f"Row {row_idx}: could not parse units '{raw}'"
            )
            return None

    def _clean_description(self, raw: str) -> str:
        # NJ India scheme names are already clean — skip base cleaning
        return raw