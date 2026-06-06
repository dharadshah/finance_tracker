from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from datetime import datetime, timezone

from finance_tracker.database import get_session
from finance_tracker.models.categorisation import LearnedRule
from finance_tracker.models.transaction import Category
from finance_tracker.models.transaction import Transaction as TxnModel
from finance_tracker.models.categorisation import CategorizationLog



router = APIRouter(prefix="/api/rules", tags=["rules"])


class RuleCreate(BaseModel):
    institution: str
    description_pattern: str
    category_name: str


class RuleResponse(BaseModel):
    id: int
    institution: str
    description_pattern: str
    category_name: str
    match_count: int
    last_seen_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[RuleResponse])
def list_rules():
    with get_session() as session:
        rules = session.execute(
            select(LearnedRule).order_by(
                LearnedRule.institution,
                LearnedRule.match_count.desc(),
            )
        ).scalars().all()
        return [RuleResponse.model_validate(r) for r in rules]


@router.post("/", response_model=RuleResponse, status_code=201)
def create_rule(payload: RuleCreate):
    with get_session() as session:
        # Check category exists
        cat = session.execute(
            select(Category).where(Category.name == payload.category_name)
        ).scalar()
        if not cat:
            raise HTTPException(status_code=400, detail=f"Category '{payload.category_name}' not found")

        # Check rule doesn't already exist
        existing = session.execute(
            select(LearnedRule).where(
                LearnedRule.institution == payload.institution,
                LearnedRule.description_pattern == payload.description_pattern,
            )
        ).scalar()
        if existing:
            raise HTTPException(status_code=400, detail="Rule already exists")

        rule = LearnedRule(
            institution=payload.institution,
            description_pattern=payload.description_pattern,
            category_id=cat.id,
            category_name=payload.category_name,
            match_count=1,
            last_seen_at=datetime.now(timezone.utc),
        )
        session.add(rule)
        session.flush()
        return RuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int):
    with get_session() as session:
        rule = session.get(LearnedRule, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        session.delete(rule)
        session.flush()


class CorrectionLogResponse(BaseModel):
    id: int
    transaction_id: int
    description: str
    raw_description: str | None
    category_name: str
    previous_category: str | None
    assigned_at: datetime

    model_config = {"from_attributes": True}


@router.get("/corrections", response_model=list[CorrectionLogResponse])
def list_corrections(limit: int = 50):
    with get_session() as session:
        # Get manual corrections only, most recent first
        logs = session.execute(
            select(CategorizationLog)
            .where(CategorizationLog.source == "manual")
            .order_by(CategorizationLog.assigned_at.desc())
            .limit(limit)
        ).scalars().all()

        result = []
        for log in logs:
            txn = session.get(TxnModel, log.transaction_id)
            if not txn:
                continue

            # Find previous category by looking at the log entry before this one
            prev = session.execute(
                select(CategorizationLog)
                .where(
                    CategorizationLog.transaction_id == log.transaction_id,
                    CategorizationLog.id < log.id,
                )
                .order_by(CategorizationLog.id.desc())
                .limit(1)
            ).scalar()

            result.append(CorrectionLogResponse(
                id=log.id,
                transaction_id=log.transaction_id,
                description=txn.description,
                raw_description=txn.raw_description,
                category_name=log.category_name,
                previous_category=prev.category_name if prev else None,
                assigned_at=log.assigned_at,
            ))

        return result