
import os
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


from app.db import Base, get_db
from app.deps.auth import get_current_user_id
from app.main import app
from app.models import User

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://budgeting:budgeting@localhost:5432/budgeting_test",
)


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """One engine and one schema for the whole test run.

    `create_all` reads every table registered on `Base.metadata`, which is
    populated as a side effect of importing `app.models` above.
    """
    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()
    
@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()
    

@pytest.fixture
def user(db_session: Session) -> User:
    u = User(email="owner@gmail.com", username="owner")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def other_user(db_session: Session) -> User:
    other_user = User(email="intruder@gmail.com", username="intruder")
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)
    return other_user


@pytest.fixture
def client(db_session: Session, user: User) -> Generator[TestClient, None, None]:
    user_id: uuid.UUID = user.id
    
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
