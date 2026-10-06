import uuid

from fastapi.testclient import TestClient

from app.models import Category


def test_create_category(client: TestClient) -> None:
    response = client.post(
        "/categories/",
        json={"name": "Groceries", "type": "expense"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Groceries"
    assert body["type"] == "expense"
    assert uuid.UUID(body["id"])


# Validation Tests


def test_create_category_rejects_bad_color(client: TestClient) -> None:
    response = client.post(
        "/categories/",
        json={"name": "Groceries", "color": "0000000", "type": "expense"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "color"]


def test_create_category_rejects_bad_name(client: TestClient) -> None:
    response = client.post(
        "/categories/",
        json={"name": "Super Duper Long Name that exceeds length max", "type": "expense"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "name"]


# Cross Tenant


def test_cannot_read_another_users_category(client: TestClient, other_category: Category) -> None:
    response = client.get(f"/categories/{other_category.id}")
    assert response.status_code == 404


def test_cannot_update_another_users_category(client: TestClient, other_category: Category) -> None:
    response = client.patch(
        f"/categories/{other_category.id}",
        json={"name": "Hacked"},
    )
    assert response.status_code == 404


def test_cannot_delete_another_users_category(client: TestClient, other_category: Category) -> None:
    response = client.delete(f"/categories/{other_category.id}")
    assert response.status_code == 404


def test_cannot_create_another_users_child_category(
    client: TestClient, other_category: Category
) -> None:
    response = client.post(
        "/categories/",
        json={"name": "Groceries", "type": "expense", "parent_id": f"{other_category.id}"},
    )
    assert response.status_code == 404
