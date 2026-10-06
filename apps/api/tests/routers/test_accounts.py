import uuid
from decimal import Decimal

from fastapi.testclient import TestClient

from app.models import Account


def test_create_account(client: TestClient) -> None:
    response = client.post(
        "/accounts/",
        json={"name": "Checking", "type": "checking", "initial_balance": "250.00"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Checking"
    assert Decimal(body["current_balance"]) == Decimal("250.00")
    assert body["currency"] == "USD"
    assert uuid.UUID(body["id"])


# Validation Failure tests


def test_create_account_rejects_bad_currency(client: TestClient) -> None:
    response = client.post(
        "/accounts/",
        json={"name": "Checking", "type": "checking", "currency": "usd"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "currency"]


def test_create_account_rejects_bad_type(client: TestClient) -> None:
    response = client.post(
        "/accounts/",
        json={"name": "Checking", "type": "check", "initial_balance": "250.00"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "type"]


def test_create_account_rejects_bad_name(client: TestClient) -> None:
    response = client.post(
        "/accounts/",
        json={"name": "", "type": "checking", "initial_balance": "250.00"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "name"]


# Cross - Tenant


def test_cannot_read_another_users_account(client: TestClient, other_account: Account) -> None:
    response = client.get(f"/accounts/{other_account.id}")
    assert response.status_code == 404


def test_cannot_update_another_users_account(client: TestClient, other_account: Account) -> None:
    response = client.patch(f"/accounts/{other_account.id}", json={"name": "Hacked"})
    assert response.status_code == 404


def test_cannot_delete_another_users_account(client: TestClient, other_account: Account) -> None:
    response = client.delete(f"/accounts/{other_account.id}")
    assert response.status_code == 404


# Test Pagination


def test_cannot_list_too_many_accounts(client: TestClient) -> None:
    response = client.get("/accounts/?limit=500")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "limit"]
