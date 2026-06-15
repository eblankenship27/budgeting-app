import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.enums import AccountType
from app.schemas.base import APISchema


class AccountBase(APISchema):
    name: str = Field(min_length=1, max_length=100)
    type: AccountType
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")


class AccountCreate(AccountBase):
    initial_balance: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)


class AccountUpdate(APISchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class AccountRead(AccountBase):
    id: uuid.UUID
    current_balance: Decimal
    is_active: bool
    created_at: datetime
