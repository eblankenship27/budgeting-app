import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import get_for_user
from app.db import get_db
from app.deps.auth import get_current_user_id
from app.models import Category
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate, Page, PaginationParams

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CategoryRead)
def category_create(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    if category.parent_id is not None:
        get_for_user(db, Category, category.parent_id, user_id)
    new_category = Category(
        user_id=user_id,
        name=category.name,
        type=category.type,
        color=category.color,
        parent_id=category.parent_id,
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.get("/", response_model=Page[CategoryRead])
def category_get_all(
    pagination: Annotated[PaginationParams, Query()],
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    categories = (
        db.execute(
            select(Category)
            .where(Category.user_id == user_id)
            .order_by(Category.created_at)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        .scalars()
        .all()
    )
    count = db.execute(
        select(func.count()).select_from(Category).where(Category.user_id == user_id)
    ).scalar_one()
    return Page(items=categories, total=count, limit=pagination.limit, offset=pagination.offset)


@router.get("/{category_id}", response_model=CategoryRead)
def category_get(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return get_for_user(db, Category, category_id, user_id)


@router.patch("/{category_id}", response_model=CategoryRead)
def category_update(
    category_updates: CategoryUpdate,
    category_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    category = get_for_user(db, Category, category_id, user_id)
    if category_updates.parent_id is not None:
        get_for_user(db,Category, category_updates.parent_id, user_id)
    for name, value in category_updates.model_dump(exclude_unset=True).items():
        setattr(category, name, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def category_delete(
    category_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    category = get_for_user(db, Category, category_id, user_id)
    db.delete(category)
    db.commit()
    return
