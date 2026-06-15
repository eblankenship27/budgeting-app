import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.base import APISchema


class UserBase(APISchema):
    email: EmailStr
    username: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    """For internal use — users are created via Cognito signup, not directly."""

    cognito_sub: str | None = Field(default=None, max_length=255)


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
