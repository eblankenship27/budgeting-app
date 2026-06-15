import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import APISchema


class TransactionBase(APISchema):
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    transaction_date: date
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)
    merchant: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)
    is_pending: bool = False


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(APISchema):
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    transaction_date: date | None = None
    amount: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    merchant: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)
    is_pending: bool | None = None


class TransactionRead(TransactionBase):
    id: uuid.UUID
    created_at: datetime
    external_id: str | None = None
