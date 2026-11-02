"""Security and response tests for the admin user directory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.v1.auth import get_auth_service
from app.main import app
from bson import ObjectId
from fastapi.testclient import TestClient


@pytest.fixture
def setup_client():
    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            yield client, auth
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_requires_authentication(setup_client):
    client, _ = setup_client

    response = client.get("/api/v1/admin/users?role=teacher")

    assert response.status_code == 401


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_rejects_non_admin(setup_client, role):
    client, auth = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": role,
    }

    response = client.get("/api/v1/admin/users?role=teacher")

    assert response.status_code == 403


def test_admin_receives_safe_user_fields(setup_client):
    client, auth = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
    }

    user_id = ObjectId()

    with patch(
        "app.api.v1.admin_users.UserRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.list_by_role = AsyncMock(
            return_value=[
                {
                    "_id": user_id,
                    "full_name": "Test Teacher",
                    "email": "teacher@example.com",
                    "role": "teacher",
                    "password_hash": "must-not-leak",
                }
            ]
        )

        response = client.get(
            "/api/v1/admin/users?role=teacher&limit=10&offset=5"
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(user_id),
            "full_name": "Test Teacher",
            "email": "teacher@example.com",
            "role": "teacher",
        }
    ]
    repository.list_by_role.assert_awaited_once_with(
        role="teacher", limit=10, offset=5
    )


@pytest.mark.parametrize(
    "query",
    [
        "role=admin",
        "role=teacher&limit=0",
        "role=student&limit=101",
        "role=teacher&offset=-1",
    ],
)
def test_rejects_invalid_filters(setup_client, query):
    client, auth = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
    }

    response = client.get(f"/api/v1/admin/users?{query}")

    assert response.status_code == 422


def test_create_teacher_requires_authentication(setup_client):
    client, _ = setup_client

    response = client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Test Teacher",
            "email": "teacher@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_create_teacher_rejects_non_admin(setup_client, role):
    client, auth = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": role,
    }
    auth.verify_csrf = AsyncMock(return_value=True)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Test Teacher",
            "email": "teacher@example.com",
            "password": "StrongPassword123!",
        },
        headers={"X-CSRF-Token": "test-token"},
    )

    assert response.status_code == 403


def test_create_teacher_rejects_invalid_csrf(setup_client):
    client, auth = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
    }
    auth.verify_csrf = AsyncMock(return_value=False)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Test Teacher",
            "email": "teacher@example.com",
            "password": "StrongPassword123!",
        },
        headers={"X-CSRF-Token": "invalid-token"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {
            "full_name": "A",
            "email": "teacher@example.com",
            "password": "StrongPassword123!",
        },
        {
            "full_name": "Test Teacher",
            "email": "invalid-email",
            "password": "StrongPassword123!",
        },
        {
            "full_name": "Test Teacher",
            "email": "teacher@example.com",
            "password": "short",
        },
    ],
)
def test_create_teacher_rejects_invalid_payload(setup_client, payload):
    client, auth = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
    }
    auth.verify_csrf = AsyncMock(return_value=True)

    response = client.post(
        "/api/v1/admin/users",
        json=payload,
        headers={"X-CSRF-Token": "test-token"},
    )

    assert response.status_code == 422


def test_create_teacher_success(setup_client):
    client, auth = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
    }
    auth.verify_csrf = AsyncMock(return_value=True)

    user_id = ObjectId()

    with (
        patch("app.api.v1.admin_users.UserRepository") as repo_class,
        patch(
            "app.api.v1.admin_users.hash_password",
            return_value="hashed-secret",
        ) as hasher,
    ):
        repository = repo_class.return_value
        repository.create = AsyncMock(
            return_value={
                "_id": user_id,
                "full_name": "Test Teacher",
                "email": "teacher@example.com",
                "role": "teacher",
                "password_hash": "hashed-secret",
            }
        )

        response = client.post(
            "/api/v1/admin/users",
            json={
                "full_name": "  Test Teacher  ",
                "email": "teacher@example.com",
                "password": "StrongPassword123!",
            },
            headers={"X-CSRF-Token": "test-token"},
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(user_id),
        "full_name": "Test Teacher",
        "email": "teacher@example.com",
        "role": "teacher",
    }
    assert "password" not in response.json()
    assert "password_hash" not in response.json()

    hasher.assert_called_once_with("StrongPassword123!")
    repository.create.assert_awaited_once_with(
        email="teacher@example.com",
        full_name="Test Teacher",
        password_hash="hashed-secret",
        role="teacher",
    )


def test_create_teacher_duplicate_email(setup_client):
    from app.repositories.users import DuplicateEmailError

    client, auth = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
    }
    auth.verify_csrf = AsyncMock(return_value=True)

    with patch(
        "app.api.v1.admin_users.UserRepository"
    ) as repo_class:
        repository = repo_class.return_value
        repository.create = AsyncMock(
            side_effect=DuplicateEmailError()
        )

        response = client.post(
            "/api/v1/admin/users",
            json={
                "full_name": "Test Teacher",
                "email": "teacher@example.com",
                "password": "StrongPassword123!",
            },
            headers={"X-CSRF-Token": "test-token"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"
