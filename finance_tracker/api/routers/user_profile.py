"""
API router for user risk profile.
One profile per owner — read by the LLM rebalancing agent at runtime.
"""

from decimal import Decimal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from finance_tracker.database import get_session
from finance_tracker.models.user_profile import UserProfile
from sqlalchemy import select

router = APIRouter(prefix="/api/profile", tags=["user_profile"])


class UserProfileRequest(BaseModel):
    owner:                    str
    age:                      int | None = None
    risk_tolerance:           str | None = None  # conservative / moderate / aggressive
    investment_horizon:       int | None = None  # years
    target_equity_pct:        float | None = None
    target_debt_pct:          float | None = None
    target_gold_pct:          float | None = None
    target_international_pct: float | None = None
    target_other_pct:         float | None = None
    notes:                    str | None = None


class UserProfileResponse(BaseModel):
    id:                       int
    owner:                    str
    age:                      int | None
    risk_tolerance:           str | None
    investment_horizon:       int | None
    target_equity_pct:        float | None
    target_debt_pct:          float | None
    target_gold_pct:          float | None
    target_international_pct: float | None
    target_other_pct:         float | None
    notes:                    str | None
    derived_targets:          dict | None = None

    model_config = {"from_attributes": True}


def _derive_targets(age: int | None, risk: str | None) -> dict:
    """
    Rule-based target allocation when user hasn't set explicit targets.
    Based on standard age-based glide path + risk adjustment.
    """
    if not age and not risk:
        return {}

    # Base equity from age: 100 - age (classic rule)
    base_equity = max(30, min(90, 100 - (age or 35)))

    # Adjust for risk tolerance
    adjustments = {
        "conservative": -15,
        "moderate":       0,
        "aggressive":   +10,
    }
    adj = adjustments.get(risk or "moderate", 0)
    equity = max(20, min(90, base_equity + adj))

    # International allocation: 10-20% of equity portion
    international = round(equity * 0.15)
    pure_equity   = equity - international

    # Remaining split between debt and gold
    remaining = 100 - equity
    gold = min(10, round(remaining * 0.25))
    debt = remaining - gold

    return {
        "equity":        pure_equity,
        "international": international,
        "debt":          debt,
        "gold":          gold,
        "other":         0,
    }


@router.post("/", response_model=UserProfileResponse)
def upsert_profile(req: UserProfileRequest):
    """Create or update profile for an owner."""
    with get_session() as session:
        existing = session.execute(
            select(UserProfile).where(UserProfile.owner == req.owner)
        ).scalar()

        if existing:
            existing.age                      = req.age
            existing.risk_tolerance           = req.risk_tolerance
            existing.investment_horizon       = req.investment_horizon
            existing.target_equity_pct        = Decimal(str(req.target_equity_pct))        if req.target_equity_pct        is not None else None
            existing.target_debt_pct          = Decimal(str(req.target_debt_pct))          if req.target_debt_pct          is not None else None
            existing.target_gold_pct          = Decimal(str(req.target_gold_pct))          if req.target_gold_pct          is not None else None
            existing.target_international_pct = Decimal(str(req.target_international_pct)) if req.target_international_pct is not None else None
            existing.target_other_pct         = Decimal(str(req.target_other_pct))         if req.target_other_pct         is not None else None
            existing.notes                    = req.notes
            profile = existing
        else:
            profile = UserProfile(
                owner=req.owner,
                age=req.age,
                risk_tolerance=req.risk_tolerance,
                investment_horizon=req.investment_horizon,
                target_equity_pct        = Decimal(str(req.target_equity_pct))        if req.target_equity_pct        is not None else None,
                target_debt_pct          = Decimal(str(req.target_debt_pct))          if req.target_debt_pct          is not None else None,
                target_gold_pct          = Decimal(str(req.target_gold_pct))          if req.target_gold_pct          is not None else None,
                target_international_pct = Decimal(str(req.target_international_pct)) if req.target_international_pct is not None else None,
                target_other_pct         = Decimal(str(req.target_other_pct))         if req.target_other_pct         is not None else None,
                notes=req.notes,
            )
            session.add(profile)

        session.flush()

        derived = None
        if not req.target_equity_pct:
            derived = _derive_targets(req.age, req.risk_tolerance)

        return UserProfileResponse(
            id=profile.id,
            owner=profile.owner,
            age=profile.age,
            risk_tolerance=profile.risk_tolerance,
            investment_horizon=profile.investment_horizon,
            target_equity_pct=float(profile.target_equity_pct) if profile.target_equity_pct else None,
            target_debt_pct=float(profile.target_debt_pct) if profile.target_debt_pct else None,
            target_gold_pct=float(profile.target_gold_pct) if profile.target_gold_pct else None,
            target_international_pct=float(profile.target_international_pct) if profile.target_international_pct else None,
            target_other_pct=float(profile.target_other_pct) if profile.target_other_pct else None,
            notes=profile.notes,
            derived_targets=derived,
        )


@router.get("/{owner}", response_model=UserProfileResponse)
def get_profile(owner: str):
    """Get profile for an owner. Returns derived targets if explicit ones not set."""
    with get_session() as session:
        profile = session.execute(
            select(UserProfile).where(UserProfile.owner == owner)
        ).scalar()

        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"No profile found for owner '{owner}'. Create one first."
            )

        derived = None
        if not profile.target_equity_pct:
            derived = _derive_targets(profile.age, profile.risk_tolerance)

        return UserProfileResponse(
            id=profile.id,
            owner=profile.owner,
            age=profile.age,
            risk_tolerance=profile.risk_tolerance,
            investment_horizon=profile.investment_horizon,
            target_equity_pct=float(profile.target_equity_pct) if profile.target_equity_pct else None,
            target_debt_pct=float(profile.target_debt_pct) if profile.target_debt_pct else None,
            target_gold_pct=float(profile.target_gold_pct) if profile.target_gold_pct else None,
            target_international_pct=float(profile.target_international_pct) if profile.target_international_pct else None,
            target_other_pct=float(profile.target_other_pct) if profile.target_other_pct else None,
            notes=profile.notes,
            derived_targets=derived,
        )