"""
Portfolio analysis engine for rebalancing recommendations.
Pure Python — no LLM calls. Produces structured findings
that the Groq agent (Phase 4) consumes as context.

Usage:
    analyzer = PortfolioAnalyzer()
    analysis = analyzer.analyze(owner="Dhara")
    # analysis is a dict with keys:
    # asset_allocation, problem_funds, overlaps,
    # sector_concentration, tax_estimates
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_tracker.database import get_session
from finance_tracker.models.investment import MFHolding, MFNavHistory, MFTransaction
from finance_tracker.models.fund_metadata import FundMetadata
from finance_tracker.models.user_profile import UserProfile
from finance_tracker.models.account import Account

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data classes for analysis output
# ------------------------------------------------------------------

@dataclass
class HoldingWithMeta:
    """A holding enriched with fund metadata and current value."""
    scheme_name:    str
    folio_number:   str
    units:          float
    avg_nav:        float
    invested:       float
    current_nav:    float
    current_value:  float
    pnl:            float
    pnl_pct:        float
    asset_class:    str
    sub_category:   str
    fund_house:     str
    scheme_code:    str
    weight_pct:     float   # % of total portfolio


@dataclass
class AssetAllocationResult:
    current:  dict[str, float]   # {asset_class: current_pct}
    target:   dict[str, float]   # {asset_class: target_pct}
    gaps:     dict[str, float]   # {asset_class: gap (+ve = overweight)}
    total_value: float


@dataclass
class ProblemFund:
    scheme_name:  str
    folio_number: str
    issue:        str    # "small_allocation" / "stale_nav" / "unmatched_metadata"
    severity:     str    # "high" / "medium" / "low"
    detail:       str


@dataclass
class OverlapPair:
    fund_a:       str
    fund_b:       str
    overlap_type: str    # "same_subcategory" / "same_amc_same_category"
    severity:     str
    detail:       str


@dataclass
class SectorConcentration:
    sub_category: str
    weight_pct:   float
    fund_count:   int
    funds:        list[str]
    is_excessive: bool
    threshold_pct: float


@dataclass
class TaxEstimate:
    scheme_name:          str
    folio_number:         str
    first_buy_date:       date | None
    holding_months:       int
    tax_type:             str    # "STCG" / "LTCG" / "unknown"
    unrealised_gain:      float
    estimated_tax:        float
    effective_tax_rate:   float


@dataclass
class PortfolioAnalysis:
    owner:                str
    analysis_date:        date
    total_value:          float
    total_invested:       float
    total_pnl:            float
    holdings:             list[HoldingWithMeta]
    asset_allocation:     AssetAllocationResult | None
    problem_funds:        list[ProblemFund]
    overlaps:             list[OverlapPair]
    sector_concentration: list[SectorConcentration]
    tax_estimates:        list[TaxEstimate]
    warnings:             list[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Main analyzer
# ------------------------------------------------------------------

class PortfolioAnalyzer:

    LTCG_EXEMPTION    = 125000.0   # Rs. 1.25L annual exemption
    LTCG_RATE         = 0.125      # 12.5%
    STCG_RATE         = 0.20       # 20%
    SMALL_ALLOC_PCT   = 2.0        # holdings below this % are flagged
    SECTOR_THRESHOLD  = 20.0       # sectoral > 20% of equity is excessive

    def analyze(self, owner: str) -> PortfolioAnalysis:
        with get_session() as session:
            profile  = self._load_profile(session, owner)
            holdings = self._load_holdings_with_meta(session, owner)

            if not holdings:
                return PortfolioAnalysis(
                    owner=owner,
                    analysis_date=date.today(),
                    total_value=0,
                    total_invested=0,
                    total_pnl=0,
                    holdings=[],
                    asset_allocation=None,
                    problem_funds=[],
                    overlaps=[],
                    sector_concentration=[],
                    tax_estimates=[],
                    warnings=["No holdings found for this owner"],
                )

            total_value    = sum(h.current_value for h in holdings)
            total_invested = sum(h.invested for h in holdings)
            total_pnl      = total_value - total_invested

            # Set weight_pct on each holding
            for h in holdings:
                h.weight_pct = (h.current_value / total_value * 100) if total_value else 0

            alloc       = self._analyze_asset_allocation(holdings, profile, total_value)
            problems    = self._detect_problem_funds(holdings)
            overlaps    = self._detect_overlaps(holdings)
            sector      = self._analyze_sector_concentration(holdings, total_value)
            tax         = self._estimate_tax(session, holdings)

            return PortfolioAnalysis(
                owner=owner,
                analysis_date=date.today(),
                total_value=total_value,
                total_invested=total_invested,
                total_pnl=total_pnl,
                holdings=holdings,
                asset_allocation=alloc,
                problem_funds=problems,
                overlaps=overlaps,
                sector_concentration=sector,
                tax_estimates=tax,
            )

    # ------------------------------------------------------------------
    # Step 1 — Asset Allocation
    # ------------------------------------------------------------------

    def _analyze_asset_allocation(
        self,
        holdings: list[HoldingWithMeta],
        profile:  UserProfile | None,
        total_value: float,
    ) -> AssetAllocationResult:

        # Current allocation
        current: dict[str, float] = {}
        for h in holdings:
            ac = h.asset_class or "Other"
            current[ac] = current.get(ac, 0.0) + h.current_value

        current_pct = {
            k: round(v / total_value * 100, 1)
            for k, v in current.items()
        } if total_value else {}

        # Target allocation — from profile or derived
        target_pct: dict[str, float] = {}
        if profile:
            if profile.target_equity_pct:
                target_pct["Equity"]        = float(profile.target_equity_pct)
                target_pct["Debt"]          = float(profile.target_debt_pct or 0)
                target_pct["Gold"]          = float(profile.target_gold_pct or 0)
                target_pct["International"] = float(profile.target_international_pct or 0)
                target_pct["Other"]         = float(profile.target_other_pct or 0)
            else:
                # Use derived targets from _derive_targets logic
                age  = profile.age or 35
                risk = profile.risk_tolerance or "moderate"
                base_equity   = max(30, min(90, 100 - age))
                adj           = {"conservative": -15, "moderate": 0, "aggressive": 10}.get(risk, 0)
                equity        = max(20, min(90, base_equity + adj))
                international = round(equity * 0.15)
                pure_equity   = equity - international
                remaining     = 100 - equity
                gold          = min(10, round(remaining * 0.25))
                debt          = remaining - gold
                target_pct    = {
                    "Equity":        pure_equity,
                    "International": international,
                    "Debt":          debt,
                    "Gold":          gold,
                    "Other":         0,
                }

        # Gaps: positive = overweight, negative = underweight
        all_classes = set(list(current_pct.keys()) + list(target_pct.keys()))
        gaps = {
            ac: round(current_pct.get(ac, 0) - target_pct.get(ac, 0), 1)
            for ac in all_classes
        }

        return AssetAllocationResult(
            current=current_pct,
            target=target_pct,
            gaps=gaps,
            total_value=total_value,
        )

    # ------------------------------------------------------------------
    # Step 2 — Problem Fund Detection
    # ------------------------------------------------------------------

    def _detect_problem_funds(
        self, holdings: list[HoldingWithMeta]
    ) -> list[ProblemFund]:
        problems = []

        for h in holdings:
            # Small allocation
            if h.weight_pct < self.SMALL_ALLOC_PCT:
                problems.append(ProblemFund(
                    scheme_name=h.scheme_name,
                    folio_number=h.folio_number,
                    issue="small_allocation",
                    severity="medium",
                    detail=f"Only {h.weight_pct:.1f}% of portfolio — too small to be meaningful",
                ))

            # Missing metadata
            if not h.asset_class or h.asset_class == "Other":
                problems.append(ProblemFund(
                    scheme_name=h.scheme_name,
                    folio_number=h.folio_number,
                    issue="unmatched_metadata",
                    severity="low",
                    detail="Fund metadata not found — asset class unknown",
                ))

        return problems

    # ------------------------------------------------------------------
    # Step 3 — Overlap Detection
    # ------------------------------------------------------------------

    def _detect_overlaps(
        self, holdings: list[HoldingWithMeta]
    ) -> list[OverlapPair]:
        overlaps = []
        n = len(holdings)

        for i in range(n):
            for j in range(i + 1, n):
                a, b = holdings[i], holdings[j]

                # Same sub-category (e.g. two Mid Cap funds)
                if (a.sub_category and b.sub_category
                        and a.sub_category == b.sub_category
                        and a.sub_category not in ("Other", "ETF", "Index")):
                    overlaps.append(OverlapPair(
                        fund_a=a.scheme_name,
                        fund_b=b.scheme_name,
                        overlap_type="same_subcategory",
                        severity="high" if a.sub_category in (
                            "Mid Cap", "Small Cap", "Large Cap", "Flexi Cap"
                        ) else "medium",
                        detail=f"Both are {a.sub_category} funds — high portfolio overlap",
                    ))

                # Same AMC, same sub-category
                elif (a.fund_house and b.fund_house
                      and a.fund_house == b.fund_house
                      and a.sub_category == b.sub_category):
                    overlaps.append(OverlapPair(
                        fund_a=a.scheme_name,
                        fund_b=b.scheme_name,
                        overlap_type="same_amc_same_category",
                        severity="high",
                        detail=f"Same AMC ({a.fund_house}) and same category — redundant",
                    ))

        return overlaps

    # ------------------------------------------------------------------
    # Step 4 — Sector Concentration
    # ------------------------------------------------------------------

    def _analyze_sector_concentration(
        self,
        holdings: list[HoldingWithMeta],
        total_value: float,
    ) -> list[SectorConcentration]:
        if not total_value:
            return []

        # Group by sub_category
        groups: dict[str, list[HoldingWithMeta]] = {}
        for h in holdings:
            sc = h.sub_category or "Other"
            groups.setdefault(sc, []).append(h)

        result = []
        for sub_cat, funds in groups.items():
            weight = sum(f.current_value for f in funds) / total_value * 100
            is_excessive = (
                sub_cat in ("Sectoral / Thematic",)
                and weight > self.SECTOR_THRESHOLD
            )
            result.append(SectorConcentration(
                sub_category=sub_cat,
                weight_pct=round(weight, 1),
                fund_count=len(funds),
                funds=[f.scheme_name for f in funds],
                is_excessive=is_excessive,
                threshold_pct=self.SECTOR_THRESHOLD,
            ))

        return sorted(result, key=lambda x: x.weight_pct, reverse=True)

    # ------------------------------------------------------------------
    # Step 5 — Tax Estimation
    # ------------------------------------------------------------------

    def _estimate_tax(
        self,
        session: Session,
        holdings: list[HoldingWithMeta],
    ) -> list[TaxEstimate]:
        today = date.today()
        estimates = []

        for h in holdings:
            if h.pnl <= 0:
                estimates.append(TaxEstimate(
                    scheme_name=h.scheme_name,
                    folio_number=h.folio_number,
                    first_buy_date=None,
                    holding_months=0,
                    tax_type="no_gain",
                    unrealised_gain=h.pnl,
                    estimated_tax=0.0,
                    effective_tax_rate=0.0,
                ))
                continue

            # Get earliest buy date for this folio
            first_buy = session.execute(
                select(MFTransaction.txn_date)
                .where(
                    MFTransaction.folio_number == h.folio_number,
                    MFTransaction.order_type   == "buy",
                )
                .order_by(MFTransaction.txn_date)
                .limit(1)
            ).scalar()

            if not first_buy:
                estimates.append(TaxEstimate(
                    scheme_name=h.scheme_name,
                    folio_number=h.folio_number,
                    first_buy_date=None,
                    holding_months=0,
                    tax_type="unknown",
                    unrealised_gain=h.pnl,
                    estimated_tax=0.0,
                    effective_tax_rate=0.0,
                ))
                continue

            holding_months = (today.year - first_buy.year) * 12 + (
                today.month - first_buy.month
            )

            if holding_months >= 12:
                tax_type = "LTCG"
                taxable  = max(0, h.pnl - self.LTCG_EXEMPTION)
                tax      = taxable * self.LTCG_RATE
            else:
                tax_type = "STCG"
                taxable  = h.pnl
                tax      = taxable * self.STCG_RATE

            rate = (tax / h.pnl * 100) if h.pnl else 0

            estimates.append(TaxEstimate(
                scheme_name=h.scheme_name,
                folio_number=h.folio_number,
                first_buy_date=first_buy,
                holding_months=holding_months,
                tax_type=tax_type,
                unrealised_gain=round(h.pnl, 2),
                estimated_tax=round(tax, 2),
                effective_tax_rate=round(rate, 2),
            ))

        return estimates

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_profile(
        self, session: Session, owner: str
    ) -> UserProfile | None:
        return session.execute(
            select(UserProfile).where(UserProfile.owner == owner)
        ).scalar()

    def _load_holdings_with_meta(
        self, session: Session, owner: str
    ) -> list[HoldingWithMeta]:
        # Get Kuvera account for this owner
        account = session.execute(
            select(Account).where(
                Account.institution == "Kuvera",
                Account.owner       == owner,
            )
        ).scalar()

        if not account:
            logger.warning("No Kuvera account for owner: %s", owner)
            return []

        holdings = session.execute(
            select(MFHolding).where(MFHolding.account_id == account.id)
        ).scalars().all()

        # Latest NAVs
        from sqlalchemy import func
        subq = (
            select(
                MFNavHistory.scheme_code,
                func.max(MFNavHistory.nav_date).label("latest_date"),
            )
            .group_by(MFNavHistory.scheme_code)
            .subquery()
        )
        nav_rows = session.execute(
            select(MFNavHistory).join(
                subq,
                (MFNavHistory.scheme_code == subq.c.scheme_code) &
                (MFNavHistory.nav_date    == subq.c.latest_date),
            )
        ).scalars().all()
        nav_map = {r.scheme_name.lower().strip(): float(r.nav) for r in nav_rows}

        # Fund metadata
        meta_rows = session.execute(select(FundMetadata)).scalars().all()
        meta_map  = {m.kuvera_scheme_name.lower().strip(): m for m in meta_rows}

        result = []
        for h in holdings:
            name_key    = h.scheme_name.lower().strip()
            current_nav = nav_map.get(name_key, float(h.avg_nav))
            meta        = meta_map.get(name_key)

            invested      = float(h.invested_amount or 0)
            current_value = float(h.units) * current_nav
            pnl           = current_value - invested
            pnl_pct       = (pnl / invested * 100) if invested else 0

            result.append(HoldingWithMeta(
                scheme_name=h.scheme_name,
                folio_number=h.folio_number,
                units=float(h.units),
                avg_nav=float(h.avg_nav),
                invested=invested,
                current_nav=current_nav,
                current_value=current_value,
                pnl=pnl,
                pnl_pct=pnl_pct,
                asset_class=meta.asset_class   if meta else "Other",
                sub_category=meta.sub_category if meta else "Other",
                fund_house=meta.fund_house      if meta else "",
                scheme_code=meta.scheme_code    if meta else "",
                weight_pct=0.0,
            ))

        return result