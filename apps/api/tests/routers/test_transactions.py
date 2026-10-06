import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.models import Account, Category, Transaction


def test_create_transaction(client: TestClient, account: Account) -> None:
    response = client.post(
        "/transactions/",
        json={
            "account_id": str(account.id),
            "transaction_date": str(date(2026, 1, 1)),
            "amount": "250.00",
            "description": "Groceries from market",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["amount"]) == Decimal("250.00")
    assert body["description"] == "Groceries from market"
    assert body["account_id"] == str(account.id)
    assert uuid.UUID(body["id"])


# Validation Tests


def test_create_transaction_rejects_bad_amount(client: TestClient, account: Account) -> None:
    response = client.post(
        "/transactions/",
        json={
            "account_id": str(account.id),
            "transaction_date": str(date(2026, 1, 1)),
            "amount": "1.123",
            "description": "Oddly specific cents",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "amount"]


# Cross Tenant


def test_cannot_get_another_users_transaction(
    client: TestClient, other_transaction: Transaction
) -> None:
    response = client.get(f"/transactions/{other_transaction.id}")
    assert response.status_code == 404


def test_cannot_update_another_users_transaction(
    client: TestClient, other_transaction: Transaction
) -> None:
    response = client.patch(
        f"/transactions/{other_transaction.id}",
        json={"description": "Hacked"},
    )
    assert response.status_code == 404


def test_cannot_delete_another_users_transaction(
    client: TestClient, other_transaction: Transaction
) -> None:
    response = client.delete(f"/transactions/{other_transaction.id}")
    assert response.status_code == 404


def test_cannot_reassign_transaction_another_users_account(
    client: TestClient, transaction: Transaction, other_account: Account
) -> None:
    response = client.patch(
        f"/transactions/{transaction.id}",
        json={"account_id": str(other_account.id)},
    )
    assert response.status_code == 404


def test_cannot_create_with_another_users_account(
    client: TestClient, other_account: Account
) -> None:
    response = client.post(
        "/transactions/",
        json={
            "account_id": str(other_account.id),
            "transaction_date": str(date(2026, 1, 1)),
            "amount": "20.83",
            "description": "Hacked",
        },
    )
    assert response.status_code == 404


def test_cannot_create_with_another_users_category(
    client: TestClient, account: Account, other_category: Category
) -> None:
    response = client.post(
        "/transactions/",
        json={
            "account_id": str(account.id),
            "category_id": str(other_category.id),
            "transaction_date": str(date(2026, 1, 1)),
            "amount": "500.00",
            "description": "Hacked",
        },
    )
    assert response.status_code == 404
