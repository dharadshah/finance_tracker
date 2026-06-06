from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from finance_tracker.database import get_session
from finance_tracker.models.transaction import Category

router = APIRouter(prefix="/api/categories", tags=["categories"])


# Schemas
class CategoryCreate(BaseModel):
    name: str
    parent_name: str | None = None
    txn_type: str = "expense"


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_name: str | None = None
    txn_type: str | None = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_name: str | None
    txn_type: str

    model_config = {"from_attributes": True}


# Routes
@router.get("/", response_model=list[CategoryResponse])
def list_categories():
    with get_session() as session:
        cats = session.execute(
            select(Category).order_by(Category.parent_name, Category.name)
        ).scalars().all()
        return [CategoryResponse.model_validate(c) for c in cats]


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(payload: CategoryCreate):
    with get_session() as session:
        existing = session.execute(
            select(Category).where(Category.name == payload.name)
        ).scalar()
        if existing:
            raise HTTPException(status_code=400, detail="Category already exists")
        cat = Category(
            name=payload.name,
            parent_name=payload.parent_name,
            txn_type=payload.txn_type,
        )
        session.add(cat)
        session.flush()
        return CategoryResponse.model_validate(cat)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, payload: CategoryUpdate):
    with get_session() as session:
        cat = session.get(Category, category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        update_data = payload.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(cat, field, value)
        session.flush()
        return CategoryResponse.model_validate(cat)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int):
    with get_session() as session:
        cat = session.get(Category, category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        session.delete(cat)
        session.flush()