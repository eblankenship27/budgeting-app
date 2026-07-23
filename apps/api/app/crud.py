import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import UserOwned


def get_for_user[ModelT: UserOwned](
    db: Session, model: type[ModelT], row_id: uuid.UUID, user_id: uuid.UUID
) -> ModelT:
    """"""
    result = db.execute(
        select(model).where(model.id == row_id, model.user_id == user_id)
    ).scalar_one_or_none()

    if result is None:
        raise HTTPException(404, detail="Not found for user")

    return result
