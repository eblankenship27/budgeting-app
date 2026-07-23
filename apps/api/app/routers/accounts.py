import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import get_for_user
from app.db import get_db
from app.deps.auth import get_current_user_id
from app.models import Account
from app.schemas import AccountCreate, AccountRead, AccountUpdate, Page, PaginationParams

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AccountRead)
def account_create(
    account: AccountCreate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    new_account = Account(
        name=account.name,
        type=account.type,
        current_balance=account.initial_balance,
        currency=account.currency,
        user_id=user_id,
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


@router.get("/", response_model=Page[AccountRead])
def get_all_accounts(
    pagination: Annotated[PaginationParams, Query()],
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    accounts = (
        db.execute(
            select(Account)
            .where(Account.user_id == user_id)
            .order_by(Account.created_at)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        .scalars()
        .all()
    )
    count = db.execute(
        select(func.count()).select_from(Account).where(Account.user_id == user_id)
    ).scalar_one()
    return Page(items=accounts, total=count, limit=pagination.limit, offset=pagination.offset)


@router.get("/{account_id}", response_model=AccountRead)
def account_get(
    account_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_for_user(db, Account, account_id, user_id)


@router.patch("/{account_id}", response_model=AccountRead)
def account_update(
    account_updates: AccountUpdate,
    account_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    account = get_for_user(db, Account, account_id, user_id)
    for name, value in account_updates.model_dump(exclude_unset=True).items():
        setattr(account, name, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def account_delete(
    account_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    account = get_for_user(db, Account, account_id, user_id)
    db.delete(account)
    db.commit()
    return
