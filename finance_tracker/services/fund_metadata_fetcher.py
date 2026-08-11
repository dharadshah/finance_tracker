"""
Fetches fund metadata from MFAPI for all schemes in mf_holdings.

Flow:
  1. Load all holdings from mf_holdings
  2. Match each holding name to real AMFI scheme_code using bulk NAV file
     (reuses NAVFetcher._match_name logic)
  3. Call MFAPI /mf/{scheme_code} for fund_house, scheme_category, scheme_type
  4. Derive asset_class and sub_category from scheme_category
  5. Upsert into fund_metadata
"""

import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_tracker.models.fund_metadata import FundMetadata
from finance_tracker.models.investment import MFHolding
from finance_tracker.services.nav_fetcher import AMFI_URL, NAVFetcher

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in/mf"


# ------------------------------------------------------------------
# Asset class derivation
# ------------------------------------------------------------------

_ASSET_CLASS_MAP = [
    ("equity scheme",       "Equity"),
    ("debt scheme",         "Debt"),
    ("hybrid scheme",       "Hybrid"),
    ("solution oriented",   "Other"),
    ("gold etf",            "Gold"),
    ("gold fund",           "Gold"),
    ("fof overseas",        "International"),
    ("overseas fund",       "International"),
    ("other scheme",        "Other"),
]

_SUB_CATEGORY_MAP = [
    ("large cap",              "Large Cap"),
    ("mid cap",                "Mid Cap"),
    ("small cap",              "Small Cap"),
    ("flexi cap",              "Flexi Cap"),
    ("multi cap",              "Multi Cap"),
    ("large & mid cap",        "Large & Mid Cap"),
    ("elss",                   "ELSS"),
    ("sectoral",               "Sectoral / Thematic"),
    ("thematic",               "Sectoral / Thematic"),
    ("index fund",             "Index"),
    ("etf",                    "ETF"),
    ("liquid",                 "Liquid"),
    ("overnight",              "Overnight"),
    ("ultra short",            "Ultra Short Duration"),
    ("short duration",         "Short Duration"),
    ("medium duration",        "Medium Duration"),
    ("long duration",          "Long Duration"),
    ("gilt",                   "Gilt"),
    ("corporate bond",         "Corporate Bond"),
    ("credit risk",            "Credit Risk"),
    ("dynamic bond",           "Dynamic Bond"),
    ("arbitrage",              "Arbitrage"),
    ("balanced advantage",     "Balanced Advantage"),
    ("aggressive hybrid",      "Aggressive Hybrid"),
    ("conservative hybrid",    "Conservative Hybrid"),
    ("multi asset",            "Multi Asset"),
    ("focused",                "Focused"),
    ("value",                  "Value / Contra"),
    ("contra",                 "Value / Contra"),
    ("dividend yield",         "Dividend Yield"),
    ("international",          "International"),
    ("fof",                    "Fund of Funds"),
]


def _derive_asset_class(scheme_category: str) -> str:
    cat = scheme_category.lower()
    for keyword, asset_class in _ASSET_CLASS_MAP:
        if keyword in cat:
            return asset_class
    return "Other"


def _derive_sub_category(scheme_category: str) -> str:
    cat = scheme_category.lower()
    for keyword, sub_cat in _SUB_CATEGORY_MAP:
        if keyword in cat:
            return sub_cat
    return "Other"


# ------------------------------------------------------------------
# Fetcher
# ------------------------------------------------------------------

class FundMetadataFetcher:
    """
    Enriches mf_holdings with fund metadata from MFAPI.
    Call fetch_and_store(session) from the API endpoint.
    """

    def __init__(self):
        self._nav_fetcher = NAVFetcher()
        self._nav_map: dict = {}

    def fetch_and_store(self, session: Session) -> dict:
        summary = {
            "total":    0,
            "updated":  0,
            "skipped":  0,
            "errors":   [],
        }

        holdings = session.execute(select(MFHolding)).scalars().all()
        if not holdings:
            summary["errors"].append("No holdings found in mf_holdings")
            return summary

        summary["total"] = len(holdings)

        # Build nav_map once (bulk AMFI file → name → scheme_code)
        self._nav_map = self._build_nav_map(summary)
        if not self._nav_map:
            return summary

        for holding in holdings:
            try:
                self._process_holding(holding, session, summary)
            except Exception as exc:
                msg = f"{holding.scheme_name}: {exc}"
                logger.warning("FundMetadataFetcher error: %s", msg)
                summary["errors"].append(msg)

        session.flush()
        logger.info("FundMetadata refresh complete: %s", summary)
        return summary

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_nav_map(self, summary: dict) -> dict:
        """
        Downloads AMFI bulk NAV file and builds
        {lowercase_scheme_name: (nav, nav_date, scheme_code, amfi_name)}
        Reuses NAVFetcher parsing logic.
        """
        try:
            response = httpx.get(AMFI_URL, timeout=30, follow_redirects=True)
            response.raise_for_status()
        except Exception as exc:
            summary["errors"].append(f"Failed to fetch AMFI file: {exc}")
            return {}

        from datetime import datetime as dt
        from decimal import Decimal

        nav_map = {}
        for line in response.text.splitlines():
            parts = line.strip().split(";")
            if len(parts) < 6:
                continue
            scheme_code = parts[0].strip()
            scheme_name = parts[3].strip()
            nav_str     = parts[4].strip()
            date_str    = parts[5].strip()
            if not nav_str or nav_str == "N.A." or not date_str:
                continue
            try:
                nav      = Decimal(nav_str)
                nav_date = dt.strptime(date_str, "%d-%b-%Y").date()
                nav_map[scheme_name.lower().strip()] = (
                    nav, nav_date, scheme_code, scheme_name
                )
            except Exception:
                continue

        return nav_map

    def _process_holding(
        self, holding: MFHolding, session: Session, summary: dict
    ) -> None:
        held_name = holding.scheme_name.lower().strip()

        # Step 1: resolve real AMFI scheme_code via name matching
        match = self._nav_fetcher._match_name(held_name, self._nav_map)
        if not match:
            msg = f"No AMFI match for: {holding.scheme_name}"
            logger.warning(msg)
            summary["errors"].append(msg)
            return

        _, _, scheme_code, amfi_name = match

        # Step 2: check if already exists — update linkage, skip MFAPI call
        existing = session.execute(
            select(FundMetadata).where(
                FundMetadata.scheme_code == scheme_code
            )
        ).scalar()

        if existing:
            if existing.kuvera_scheme_name != holding.scheme_name:
                existing.kuvera_scheme_name = holding.scheme_name
                existing.last_refreshed = datetime.now()
            summary["skipped"] += 1
            return

        # Step 3: call MFAPI for this scheme_code
        meta = self._fetch_mfapi_meta(scheme_code)

        fund_house      = meta.get("fund_house", "")
        scheme_type     = meta.get("scheme_type", "")
        scheme_category = meta.get("scheme_category", "")

        if not scheme_category:
            msg = f"Empty metadata from MFAPI for {holding.scheme_name} (code={scheme_code})"
            logger.warning(msg)
            summary["errors"].append(msg)
            return

        asset_class  = _derive_asset_class(scheme_category)
        sub_category = _derive_sub_category(scheme_category)

        # Step 4: insert — guard against race/duplicate
        try:
            record = FundMetadata(
                scheme_code=scheme_code,
                amfi_scheme_name=amfi_name,
                kuvera_scheme_name=holding.scheme_name,
                fund_house=fund_house,
                scheme_type=scheme_type,
                scheme_category=scheme_category,
                asset_class=asset_class,
                sub_category=sub_category,
                last_refreshed=datetime.now(),
            )
            session.add(record)
            session.flush()
            summary["updated"] += 1
            logger.info(
                "Fetched metadata: %s -> %s / %s",
                holding.scheme_name, asset_class, sub_category,
            )
        except Exception as exc:
            session.rollback()
            msg = f"Insert failed for {holding.scheme_name}: {exc}"
            logger.error(msg)
            summary["errors"].append(msg)

    @staticmethod
    def _fetch_mfapi_meta(scheme_code: str) -> dict:
        """
        Calls MFAPI /mf/{scheme_code} and returns the meta dict.
        Returns empty dict on failure — caller handles gracefully.
        """
        try:
            url = f"{MFAPI_BASE}/{scheme_code}"
            response = httpx.get(url, timeout=15, follow_redirects=True)
            response.raise_for_status()
            data = response.json()
            return data.get("meta", {})
        except Exception as exc:
            logger.warning("MFAPI call failed for %s: %s", scheme_code, exc)
            return {}