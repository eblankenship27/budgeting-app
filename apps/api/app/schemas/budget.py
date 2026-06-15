import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.models.enums import BudgetPeriod
from app.schemas.base import APISchema


class BudgetBase(APISchema):
    category_id: uuid.UUID
    amount: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        gt=0,
    )
    start_date: date
    period: BudgetPeriod


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(APISchema):
    amount: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        gt=0,
    )
    category_id: uuid.UUID | None = None
    start_date: date | None = None
    period: BudgetPeriod | None = None


class BudgetRead(BudgetBase):
    id: uuid.UUID
    created_at: datetime
