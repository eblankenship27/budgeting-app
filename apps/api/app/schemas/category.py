import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import CategoryType
from app.schemas.base import APISchema


class CategoryBase(APISchema):
    name: str = Field(min_length=1, max_length=20)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    type: CategoryType
    parent_id: uuid.UUID | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(APISchema):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    type: CategoryType | None = None
    parent_id: uuid.UUID | None = None
    is_archived: bool | None = None


class CategoryRead(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    is_archived: bool
