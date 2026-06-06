from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date

from finance_tracker.database import get_session
from finance_tracker.repositories.account_repository import AccountRepository
from finance_tracker.models.account import Account
from finance_tracker.parsers.registry import PARSER_REGISTRY


router = APIRouter(prefix="/api/accounts", tags=["accounts"])


# Schemas
class AccountCreate(BaseModel):
    name: str
    account_type: str
    institution: str
    account_number_last4: str | None = None
    currency: str = "INR"
    opened_on: date | None = None
    notes: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    account_type: str | None = None
    institution: str | None = None
    account_number_last4: str | None = None
    currency: str | None = None
    opened_on: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class AccountResponse(BaseModel):
    id: int
    name: str
    account_type: str
    institution: str
    account_number_last4: str | None
    currency: str
    opened_on: date | None
    is_active: bool
    notes: str | None

    model_config = {"from_attributes": True}


# Routes
@router.get("/institutions", response_model=list[str])
def list_institutions():
    parser_institutions = {cls.INSTITUTION for cls in PARSER_REGISTRY.values()}
    # Add non-parser institutions
    extra = {"Kuvera"}
    return sorted(parser_institutions | extra)

@router.get("/", response_model=list[AccountResponse])
def list_accounts(include_inactive: bool = False):
    with get_session() as session:
        repo = AccountRepository(session)
        accounts = repo.get_all(include_inactive=include_inactive)
        return [AccountResponse.model_validate(a) for a in accounts]


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: int):
    with get_session() as session:
        repo = AccountRepository(session)
        account = repo.get_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return AccountResponse.model_validate(account)


@router.post("/", response_model=AccountResponse, status_code=201)
def create_account(payload: AccountCreate):
    with get_session() as session:
        repo = AccountRepository(session)
        account = repo.create(
            name=payload.name,
            account_type=payload.account_type,
            institution=payload.institution,
            masked_number=payload.account_number_last4,
            is_active=True,
            notes=payload.notes,
        )
        return AccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, payload: AccountUpdate):
    with get_session() as session:
        repo = AccountRepository(session)
        account = repo.get_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        update_data = payload.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(account, field, value)
        session.flush()
        return AccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int):
    with get_session() as session:
        repo = AccountRepository(session)
        account = repo.get_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        session.delete(account)
        session.flush()

