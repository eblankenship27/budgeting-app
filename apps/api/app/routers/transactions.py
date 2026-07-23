import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import get_for_user
from app.db import get_db
from app.deps.auth import get_current_user_id
from app.models import Account, Category, Transaction
from app.schemas import (
    Page,
    PaginationParams,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TransactionRead)
def transaction_create(
    transaction_create: TransactionCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_for_user(db, Account, transaction_create.account_id, user_id)
    if transaction_create.category_id is not None:
        get_for_user(db, Category, transaction_create.category_id, user_id)

    transaction = Transaction(
        account_id=transaction_create.account_id,
        amount=transaction_create.amount,
        category_id=transaction_create.category_id,
        description=transaction_create.description,
        transaction_date=transaction_create.transaction_date,
        merchant=transaction_create.merchant,
        notes=transaction_create.notes,
        is_pending=transaction_create.is_pending,
        user_id=user_id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/", response_model=Page[TransactionRead])
def transactions_get_all(
    pagination: Annotated[PaginationParams, Query()],
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    transactions = (
        db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        .scalars()
        .all()
    )
    count = db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
    ).scalar_one()
    return Page(items=transactions, total=count, limit=pagination.limit, offset=pagination.offset)


@router.get("/{transaction_id}", response_model=TransactionRead)
def transaction_get(
    transaction_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_for_user(db, Transaction, transaction_id, user_id)


@router.patch("/{transaction_id}", response_model=TransactionRead)
def transaction_update(
    transaction_updates: TransactionUpdate,
    transaction_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    transaction = get_for_user(db, Transaction, transaction_id, user_id)
    if transaction_updates.account_id is not None:
        get_for_user(db, Account, transaction_updates.account_id, user_id)
    if transaction_updates.category_id is not None:
        get_for_user(db, Category, transaction_updates.category_id, user_id)
    for name, value in transaction_updates.model_dump(exclude_unset=True).items():
        setattr(transaction, name, value)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def transaction_delete(
    transaction_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    transaction = get_for_user(db, Transaction, transaction_id, user_id)
    db.delete(transaction)
    db.commit()
    return
