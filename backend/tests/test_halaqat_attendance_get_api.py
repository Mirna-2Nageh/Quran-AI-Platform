"""HTTP tests for reading session attendance."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.v1.auth import get_auth_service
from app.api.v1.halaqat import get_service
from app.main import app
from bson import ObjectId
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def setup():
    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)

    service = MagicMock()
    service.list_session_attendance = AsyncMock(return_value=[])

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: service

    try:
        with TestClient(app) as client:
            yield client, auth, service
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def endpoint():
    return f"/api/v1/halaqat/sessions/{ObjectId()}/attendance"


def test_get_attendance_requires_authentication(setup):
    client, auth, service = setup

    response = client.get(endpoint())

    assert response.status_code == 401
    service.list_session_attendance.assert_not_awaited()


def test_get_attendance_success(setup):
    client, auth, service = setup
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "teacher",
    }

    now = datetime.now(timezone.utc)
    document = {
        "_id": ObjectId(),
        "session_id": ObjectId(),
        "student_id": ObjectId(),
        "status": "present",
        "notes": None,
        "recorded_by": ObjectId(),
        "created_at": now,
        "updated_at": now,
    }

    service.list_session_attendance.return_value = [document]

    response = client.get(endpoint())

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "present"
    assert response.json()[0]["id"] == str(document["_id"])
    service.list_session_attendance.assert_awaited_once()


def test_get_attendance_forbidden(setup):
    client, auth, service = setup
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "student",
    }

    service.list_session_attendance.side_effect = HTTPException(
        status_code=403,
        detail="Not allowed to manage this Halaqa",
    )

    response = client.get(endpoint())

    assert response.status_code == 403
    service.list_session_attendance.assert_awaited_once()
