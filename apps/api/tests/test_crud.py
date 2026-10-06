import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import get_for_user
from app.models import Account, Budget, Category, Transaction, User


def test_get_for_user_returns_own_row(
    db_session: Session, user: User, transaction: Transaction
) -> None:
    result = get_for_user(db_session, Transaction, transaction.id, user.id)
    assert result.id == transaction.id


def test_get_for_user_rejects_missing_row(db_session: Session, user: User) -> None:
    with pytest.raises(HTTPException) as excinfo:
        get_for_user(db_session, Transaction, uuid.uuid4(), user.id)
    assert excinfo.value.status_code == 404


@pytest.mark.parametrize(
    ("model", "fixture_name"),
    [
        (Account, "other_account"),
        (Category, "other_category"),
        (Transaction, "other_transaction"),
        (Budget, "other_budget"),
    ],
)
def test_get_for_user_rejects_other_users_row(
    db_session: Session,
    user: User,
    request: pytest.FixtureRequest,
    model: type,
    fixture_name: str,
) -> None:
    row = request.getfixturevalue(fixture_name)
    with pytest.raises(HTTPException) as excinfo:
        get_for_user(db_session, model, row.id, user.id)
    assert excinfo.value.status_code == 404
