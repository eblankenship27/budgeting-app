import pytest
from sqlalchemy import event

from app.config import Settings
from app.db import make_engine


class _StopBeforeConnectError(Exception):
    """Raised by the test's listener so no real network connection is attempted."""

    pass


def test_iam_auth_puts_a_fresh_token_in_the_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    s = Settings(
        database_url="postgresql+psycopg://budgeting_app@db.example.internal:5432/budgeting?sslmode=require",
        db_iam_auth=True,
    )
    engine = make_engine(s)
    seen: dict[str, object] = {}

    @event.listens_for(engine, "do_connect")
    def capture(
        dialect: object, conn_rec: object, cargs: object, cparams: dict[str, object]
    ) -> None:
        seen.update(cparams)
        raise _StopBeforeConnectError

    with pytest.raises(_StopBeforeConnectError):
        engine.connect()

    token = str(seen["password"])
    assert token.startswith("db.example.internal:5432/?Action=connect")
    assert "DBUser=budgeting_app" in token
