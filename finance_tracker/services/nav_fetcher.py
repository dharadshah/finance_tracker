import logging
import httpx
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from finance_tracker.models.investment import MFNavHistory, MFHolding

logger = logging.getLogger(__name__)

AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
DATE_FORMAT = "%d-%b-%Y"


class NAVFetcher:
    """
    Fetches latest NAV for all mutual funds from AMFI India.
    Matches funds by scheme name using fuzzy word matching.
    """

    def fetch_and_store(self, session: Session) -> dict:
        summary = {"fetched": 0, "matched": 0, "already_current": 0, "errors": []}

        # Get all held scheme names
        holdings = session.execute(select(MFHolding)).scalars().all()
        if not holdings:
            summary["errors"].append("No holdings found")
            return summary

        held_names = {h.scheme_name.lower().strip(): h for h in holdings}

        # Fetch AMFI file
        try:
            response = httpx.get(AMFI_URL, timeout=30, follow_redirects=True)
            response.raise_for_status()
            lines = response.text.splitlines()
        except Exception as e:
            summary["errors"].append(f"Failed to fetch AMFI data: {e}")
            return summary

        # Parse AMFI file
        nav_map = {}
        for line in lines:
            parts = line.strip().split(";")
            if len(parts) < 6:
                continue
            scheme_code = parts[0].strip()
            scheme_name = parts[3].strip()
            nav_str = parts[4].strip()
            date_str = parts[5].strip()

            if not nav_str or nav_str == "N.A." or not date_str:
                continue

            try:
                nav = Decimal(nav_str)
                nav_date = datetime.strptime(date_str, DATE_FORMAT).date()
                nav_map[scheme_name.lower().strip()] = (nav, nav_date, scheme_code, scheme_name)
                summary["fetched"] += 1
            except Exception:
                continue

        # Match holdings to NAV data
        already_inserted = set()  # track scheme_codes inserted this run

        for held_name, holding in held_names.items():
            match = self._match_name(held_name, nav_map)

            if not match:
                logger.warning("No NAV match found for: %s", holding.scheme_name)
                summary["errors"].append(f"No match: {holding.scheme_name}")
                continue

            nav, nav_date, scheme_code, amfi_name = match

            # Skip if already inserted in this run
            if scheme_code in already_inserted:
                summary["already_current"] += 1
                continue

            # Check if already stored for this date
            existing = session.execute(
                select(MFNavHistory).where(
                    MFNavHistory.scheme_code == scheme_code,
                    MFNavHistory.nav_date == nav_date,
                )
            ).scalar()

            if existing:
                summary["already_current"] += 1
                already_inserted.add(scheme_code)
                continue

            session.add(MFNavHistory(
                scheme_code=scheme_code,
                scheme_name=amfi_name,
                nav_date=nav_date,
                nav=nav,
            ))
            already_inserted.add(scheme_code)
            summary["matched"] += 1

        session.flush()
        logger.info("NAV fetch complete: %s", summary)
        return summary

    def _match_name(self, held_name: str, nav_map: dict) -> tuple | None:
        # Normalize: flexicap -> flexi cap, midcap -> mid cap etc.
        def normalize(name: str) -> str:
            return (name
                .replace("flexicap", "flexi cap")
                .replace("midcap", "mid cap")
                .replace("smallcap", "small cap")
                .replace("largecap", "large cap")
                .replace("multicap", "multi cap")
            )

        held_normalized = normalize(held_name)

        # 1. Exact match
        if held_normalized in nav_map:
            return nav_map[held_normalized]

        # Also try normalized nav_map keys
        for amfi_name, data in nav_map.items():
            if normalize(amfi_name) == held_normalized:
                return data

        # 2. Fuzzy word overlap
        stop_words = {
            'fund', 'plan', 'growth', 'direct', 'the', 'of', 'and',
            '-', 'regular', 'option', 'idcw', 'dividend', 'payout',
            'reinvestment', 'series', 'india', 'mutual',
        }

        held_words = set(held_normalized.lower().split()) - stop_words
        best_score = 0
        best_match = None

        for amfi_name, data in nav_map.items():
            amfi_words = set(normalize(amfi_name).lower().split()) - stop_words
            common = held_words & amfi_words
            score = len(common)
            if score > best_score and score >= 2:
                best_score = score
                best_match = data

        return best_match

    def get_latest_navs(self, session: Session) -> dict[str, tuple[Decimal, date]]:
        """
        Returns latest NAV per scheme_name from mf_nav_history.
        Used by holdings endpoint to calculate current value.
        """
        # Get latest nav_date per scheme_code
        subq = (
            select(
                MFNavHistory.scheme_code,
                func.max(MFNavHistory.nav_date).label("latest_date"),
            )
            .group_by(MFNavHistory.scheme_code)
            .subquery()
        )

        rows = session.execute(
            select(MFNavHistory).join(
                subq,
                (MFNavHistory.scheme_code == subq.c.scheme_code) &
                (MFNavHistory.nav_date == subq.c.latest_date),
            )
        ).scalars().all()

        return {
            r.scheme_name.lower().strip(): (r.nav, r.nav_date)
            for r in rows
        }