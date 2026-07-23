import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

DEV_USER_EMAIL = "fluffy2578@gmail.com"


def get_current_user_id(db: Annotated[Session, Depends(get_db)]) -> uuid.UUID:
    # TEMP: replaced by Cognito JWT claims in Phase 4
    user = db.execute(select(User).where(User.email == DEV_USER_EMAIL)).scalar_one_or_none()
    if user is None:
        user = User(email=DEV_USER_EMAIL, username="devuser")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id
