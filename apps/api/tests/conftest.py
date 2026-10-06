import os
import uuid
from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.db import Base, get_db
from app.deps.auth import get_current_user_id
from app.main import app
from app.models import (
    Account,
    AccountType,
    Budget,
    BudgetPeriod,
    Category,
    CategoryType,
    Transaction,
    User,
)

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
def account(db_session: Session, user: User) -> Account:
    account = Account(name="Checking", type=AccountType.checking, user_id=user.id)
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def other_account(db_session: Session, other_user) -> Account:
    other_account = Account(name="Checking", type=AccountType.checking, user_id=other_user.id)
    db_session.add(other_account)
    db_session.commit()
    db_session.refresh(other_account)
    return other_account


@pytest.fixture
def category(db_session: Session, user: User) -> Category:
    category = Category(name="Groceries", type=CategoryType.expense, user_id=user.id)
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def other_category(db_session: Session, other_user: User) -> Category:
    other_category = Category(name="Utilities", type=CategoryType.expense, user_id=other_user.id)
    db_session.add(other_category)
    db_session.commit()
    db_session.refresh(other_category)
    return other_category


@pytest.fixture
def transaction(db_session: Session, user: User, account: Account) -> Transaction:
    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        transaction_date=date(2026, 1, 15),
        amount=Decimal("-80.00"),
        description="Groceries",
    )
    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)
    return transaction


@pytest.fixture
def other_transaction(db_session: Session, other_user: User, other_account: Account) -> Transaction:
    other_transaction = Transaction(
        user_id=other_user.id,
        account_id=other_account.id,
        transaction_date=date(2026, 2, 20),
        amount=Decimal("-17.85"),
        description="Taco Bell",
    )
    db_session.add(other_transaction)
    db_session.commit()
    db_session.refresh(other_transaction)
    return other_transaction


@pytest.fixture
def budget(db_session: Session, user: User, category: Category) -> Budget:
    budget = Budget(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("500.00"),
        period=BudgetPeriod.monthly,
        start_date=date(2026, 1, 1),
    )
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)
    return budget


@pytest.fixture
def other_budget(db_session: Session, other_user: User, other_category: Category) -> Budget:
    other_budget = Budget(
        user_id=other_user.id,
        category_id=other_category.id,
        amount=Decimal("250.00"),
        period=BudgetPeriod.monthly,
        start_date=date(2026, 2, 1),
    )
    db_session.add(other_budget)
    db_session.commit()
    db_session.refresh(other_budget)
    return other_budget


@pytest.fixture
def client(db_session: Session, user: User) -> Generator[TestClient, None, None]:
    user_id: uuid.UUID = user.id

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
