import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.models import Budget, Category


def test_create_budget(client: TestClient, category: Category) -> None:
    response = client.post(
        "/budgets/",
        json={
            "amount": "500.00",
            "start_date": date(2026, 1, 1).isoformat(),
            "period": "monthly",
            "category_id": str(category.id),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["amount"]) == Decimal("500.00")
    assert uuid.UUID(body["id"])
    assert body["category_id"] == str(category.id)


# Validation Tests


def test_create_budget_rejects_bad_amount(client: TestClient, category: Category) -> None:
    response = client.post(
        "/budgets/",
        json={
            "amount": "0",
            "start_date": date(2026, 1, 1).isoformat(),
            "period": "monthly",
            "category_id": str(category.id),
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "amount"]


# Cross Tenant


def test_cannot_get_another_users_budget(client: TestClient, other_budget: Budget) -> None:
    response = client.get(
        f"/budgets/{other_budget.id}",
    )
    assert response.status_code == 404


def test_cannot_update_another_users_budget(client: TestClient, other_budget: Budget) -> None:
    response = client.patch(
        f"/budgets/{other_budget.id}",
        json={
            "amount": "5000",
        },
    )
    assert response.status_code == 404


def test_cannot_delete_another_users_budget(client: TestClient, other_budget: Budget) -> None:
    response = client.delete(
        f"/budgets/{other_budget.id}",
    )
    assert response.status_code == 404


def test_cannot_create_with_another_users_category(
    client: TestClient, other_category: Category
) -> None:
    response = client.post(
        "/budgets/",
        json={
            "amount": "500",
            "start_date": date(2026, 1, 1).isoformat(),
            "period": "monthly",
            "category_id": str(other_category.id),
        },
    )
    assert response.status_code == 404


def test_cannot_reassign_budget_another_users_category(
    client: TestClient, budget: Budget, other_category: Category
) -> None:
    response = client.patch(
        f"/budgets/{budget.id}",
        json={
            "category_id": str(other_category.id),
        },
    )
    assert response.status_code == 404
