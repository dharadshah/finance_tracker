"""
Groq-powered portfolio rebalancing agent.

Takes PortfolioAnalysis output from Phase 3 and produces
structured recommendations with confidence score and
plain-English advisor explanation.

Model: llama-3.3-70b-versatile (best reasoning on Groq)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date

from groq import Groq

from finance_tracker.config import settings
from finance_tracker.services.portfolio_analyzer import PortfolioAnalysis

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-oss-120b"


# ------------------------------------------------------------------
# Output data classes
# ------------------------------------------------------------------

@dataclass
class FundRecommendation:
    action:        str          # HOLD / SWITCH / EXIT / ADD / REDUCE
    fund_name:     str
    folio:         str | None
    reason:        str
    urgency:       str          # high / medium / low
    tax_note:      str | None
    switch_to:     str | None   # if action == SWITCH


@dataclass
class AllocationAction:
    asset_class:   str
    current_pct:   float
    target_pct:    float
    gap_pct:       float
    action:        str          # INCREASE / DECREASE / MAINTAIN
    how:           str          # plain English — what to buy/sell


@dataclass
class RebalancingReport:
    owner:               str
    report_date:         date
    confidence_score:    int         # 0–100
    executive_summary:   str
    key_issues:          list[str]
    fund_recommendations: list[FundRecommendation]
    allocation_actions:  list[AllocationAction]
    advisor_explanation: str         # full narrative
    warnings:            list[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Agent
# ------------------------------------------------------------------

class RebalancingAgent:

    def __init__(self):
        self._client = Groq(api_key=settings.groq_api_key)

    def generate_report(self, analysis: PortfolioAnalysis) -> RebalancingReport:
        context = self._build_context(analysis)
        logger.info("Calling Groq for rebalancing report (owner=%s)", analysis.owner)

        try:
            raw = self._call_groq(context)
            report = self._parse_response(raw, analysis)
        except Exception as exc:
            logger.error("Groq agent failed: %s", exc)
            report = RebalancingReport(
                owner=analysis.owner,
                report_date=date.today(),
                confidence_score=0,
                executive_summary="Analysis failed — please retry.",
                key_issues=[str(exc)],
                fund_recommendations=[],
                allocation_actions=[],
                advisor_explanation="",
                warnings=[f"Agent error: {exc}"],
            )

        return report

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------

    def _build_context(self, a: PortfolioAnalysis) -> str:
        alloc = a.asset_allocation

        # Top overlaps
        top_overlaps = [
            f"- {o.fund_a} <-> {o.fund_b} ({o.overlap_type}, {o.severity} severity)"
            for o in a.overlaps[:10]
        ]

        # Sector concentration
        sector_lines = [
            f"- {s.sub_category}: {s.weight_pct:.1f}% ({s.fund_count} funds)"
            + (" *** EXCESSIVE ***" if s.is_excessive else "")
            for s in a.sector_concentration[:8]
        ]

        # Problem funds (small allocation only, deduplicated)
        small_funds = list({
            p.scheme_name for p in a.problem_funds
            if p.issue == "small_allocation"
        })

        # Tax top 5
        tax_lines = []
        for t in sorted(
            a.tax_estimates, key=lambda x: x.unrealised_gain, reverse=True
        )[:5]:
            if t.unrealised_gain > 0:
                tax_lines.append(
                    f"- {t.scheme_name[:45]}: "
                    f"Gain Rs.{t.unrealised_gain:,.0f} | "
                    f"{t.tax_type} | "
                    f"Tax Rs.{t.estimated_tax:,.0f} | "
                    f"Held {t.holding_months} months"
                )

        # Holdings list
        holding_lines = [
            f"- {h.scheme_name} | {h.sub_category} | {h.asset_class} | "
            f"Rs.{h.current_value:,.0f} ({h.weight_pct:.1f}%) | "
            f"P&L: Rs.{h.pnl:,.0f}"
            for h in sorted(a.holdings, key=lambda x: x.current_value, reverse=True)
        ]

        context = f"""
You are a SEBI-registered fee-only financial advisor in India analysing a mutual fund portfolio.
Provide a detailed rebalancing report based on the data below.

=== INVESTOR PROFILE ===
Owner:               {a.owner}
Analysis Date:       {a.analysis_date}

=== PORTFOLIO SUMMARY ===
Total Current Value: Rs.{a.total_value:,.0f}
Total Invested:      Rs.{a.total_invested:,.0f}
Total P&L:           Rs.{a.total_pnl:,.0f} ({(a.total_pnl/a.total_invested*100) if a.total_invested else 0:.1f}%)
Number of Funds:     {len(a.holdings)}

=== ASSET ALLOCATION ===
{"".join([
    f"  {ac}: Current {alloc.current.get(ac,0):.1f}% | Target {alloc.target.get(ac,0):.1f}% | Gap {alloc.gaps.get(ac,0):+.1f}%\n"
    for ac in sorted(set(list(alloc.current.keys()) + list(alloc.target.keys())))
]) if alloc else "No allocation data"}

=== HOLDINGS (sorted by value) ===
{chr(10).join(holding_lines)}

=== OVERLAP PAIRS (top 10) ===
{chr(10).join(top_overlaps) if top_overlaps else "None detected"}

=== SECTOR CONCENTRATION ===
{chr(10).join(sector_lines)}

=== SMALL / FRAGMENTED FUNDS (< 2% each) ===
{chr(10).join(f'- {f}' for f in small_funds) if small_funds else "None"}

=== TAX SITUATION (top gainers) ===
{chr(10).join(tax_lines) if tax_lines else "No significant gains"}

=== YOUR TASK ===
Respond ONLY with a valid JSON object. No preamble, no markdown, no explanation outside JSON.

{{
  "confidence_score": <integer 0-100>,
  "executive_summary": "<2-3 sentence summary of the portfolio's biggest issues>",
  "key_issues": [
    "<issue 1>",
    "<issue 2>",
    "<issue 3>",
    "<issue 4>",
    "<issue 5>"
  ],
  "fund_recommendations": [
    {{
      "action": "<HOLD|SWITCH|EXIT|ADD|REDUCE>",
      "fund_name": "<exact fund name from holdings>",
      "folio": "<folio number or null>",
      "reason": "<specific reason>",
      "urgency": "<high|medium|low>",
      "tax_note": "<tax implication or null>",
      "switch_to": "<target fund name if SWITCH else null>"
    }}
  ],
  "allocation_actions": [
    {{
      "asset_class": "<Equity|Debt|Gold|International|Other>",
      "current_pct": <float>,
      "target_pct": <float>,
      "gap_pct": <float>,
      "action": "<INCREASE|DECREASE|MAINTAIN>",
      "how": "<specific actionable instruction>"
    }}
  ],
  "advisor_explanation": "<3-5 paragraph plain English explanation as a fee-only advisor would write it. Be specific about which funds to exit, which to keep, and why. Address tax implications. Give a clear action priority order.>"
}}
"""
        return context

    # ------------------------------------------------------------------
    # Groq call
    # ------------------------------------------------------------------

    def _call_groq(self, context: str) -> dict:
        response = self._client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a SEBI-registered fee-only financial advisor in India. "
                        "You give specific, actionable portfolio advice. "
                        "You always respond with valid JSON only — no markdown, no preamble."
                    ),
                },
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            max_tokens=4000,
        )

        raw_text = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        return json.loads(raw_text)

    # ------------------------------------------------------------------
    # Response parser
    # ------------------------------------------------------------------

    def _parse_response(
        self, raw: dict, analysis: PortfolioAnalysis
    ) -> RebalancingReport:
        fund_recs = [
            FundRecommendation(
                action=r.get("action", "HOLD"),
                fund_name=r.get("fund_name", ""),
                folio=r.get("folio"),
                reason=r.get("reason", ""),
                urgency=r.get("urgency", "medium"),
                tax_note=r.get("tax_note"),
                switch_to=r.get("switch_to"),
            )
            for r in raw.get("fund_recommendations", [])
        ]

        alloc_actions = [
            AllocationAction(
                asset_class=a.get("asset_class", ""),
                current_pct=float(a.get("current_pct", 0)),
                target_pct=float(a.get("target_pct", 0)),
                gap_pct=float(a.get("gap_pct", 0)),
                action=a.get("action", "MAINTAIN"),
                how=a.get("how", ""),
            )
            for a in raw.get("allocation_actions", [])
        ]

        return RebalancingReport(
            owner=analysis.owner,
            report_date=date.today(),
            confidence_score=int(raw.get("confidence_score", 50)),
            executive_summary=raw.get("executive_summary", ""),
            key_issues=raw.get("key_issues", []),
            fund_recommendations=fund_recs,
            allocation_actions=alloc_actions,
            advisor_explanation=raw.get("advisor_explanation", ""),
        )