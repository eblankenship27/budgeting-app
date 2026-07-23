import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import get_for_user
from app.db import get_db
from app.deps.auth import get_current_user_id
from app.models import Budget, Category
from app.schemas import BudgetCreate, BudgetRead, BudgetUpdate, Page, PaginationParams

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("/", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def budget_create(
    budget_create: BudgetCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_for_user(db, Category, budget_create.category_id, user_id)
    budget = Budget(
        amount=budget_create.amount,
        category_id=budget_create.category_id,
        period=budget_create.period,
        start_date=budget_create.start_date,
        user_id=user_id
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/", response_model=Page[BudgetRead])
def budgets_get_all(
    pagination: Annotated[PaginationParams, Query()],
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    budgets = (
        db.execute(
            select(Budget)
            .where(Budget.user_id == user_id)
            .order_by(Budget.created_at)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        .scalars()
        .all()
    )
    count = db.execute(
        select(func.count()).select_from(Budget).where(Budget.user_id == user_id)
    ).scalar_one()
    return Page(items=budgets, total=count, limit=pagination.limit, offset=pagination.offset)


@router.get("/{budget_id}", response_model=BudgetRead)
def budget_get(
    budget_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_for_user(db, Budget, budget_id, user_id)


@router.patch("/{budget_id}", response_model=BudgetRead)
def budget_update(
    budget_updates: BudgetUpdate,
    budget_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    budget = get_for_user(db, Budget, budget_id, user_id)
    if budget_updates.category_id is not None:
        get_for_user(db, Category, budget_updates.category_id, user_id)
    for name, value in budget_updates.model_dump(exclude_unset=True).items():
        setattr(budget, name, value)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def budget_delete(
    budget_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    budget = get_for_user(db, Budget, budget_id, user_id)
    db.delete(budget)
    db.commit()
    return
