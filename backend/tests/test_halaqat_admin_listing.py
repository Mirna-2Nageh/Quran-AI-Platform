"""Tests for admin-only Halaqat listing."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.v1.auth import get_auth_service
from app.api.v1.halaqat import get_service
from app.main import app
from bson import ObjectId
from fastapi.testclient import TestClient


@pytest.fixture
def setup_client():
    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)

    service = MagicMock()
    service.repository.list_all_halaqat = AsyncMock(return_value=[])

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: service

    try:
        with TestClient(app) as client:
            yield client, auth, service
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def test_listing_requires_authentication(setup_client):
    client, _, service = setup_client

    response = client.get("/api/v1/halaqat")

    assert response.status_code == 401
    service.repository.list_all_halaqat.assert_not_awaited()


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_listing_rejects_non_admin(setup_client, role):
    client, auth, service = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": role,
        "is_active": True,
    }

    response = client.get("/api/v1/halaqat")

    assert response.status_code == 403
    service.repository.list_all_halaqat.assert_not_awaited()


def test_admin_receives_halaqat(setup_client):
    client, auth, service = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
        "is_active": True,
    }

    halaqa_id = ObjectId()
    teacher_id = ObjectId()
    now = datetime.now(timezone.utc)

    service.repository.list_all_halaqat.return_value = [
        {
            "_id": halaqa_id,
            "name": "Beginners",
            "description": "First Halaqa",
            "teacher_id": teacher_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    ]

    response = client.get(
        "/api/v1/halaqat?limit=10&offset=5"
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(halaqa_id)
    assert data[0]["teacher_id"] == str(teacher_id)
    assert data[0]["name"] == "Beginners"
    assert data[0]["status"] == "active"

    service.repository.list_all_halaqat.assert_awaited_once_with(
        limit=10,
        offset=5,
    )


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "offset=-1",
        "limit=abc",
    ],
)
def test_listing_rejects_invalid_pagination(setup_client, query):
    client, auth, service = setup_client
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
        "is_active": True,
    }

    response = client.get(f"/api/v1/halaqat?{query}")

    assert response.status_code == 422
    service.repository.list_all_halaqat.assert_not_awaited()
