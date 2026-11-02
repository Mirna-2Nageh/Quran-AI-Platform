"""HTTP tests for attendance recording."""

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
    auth.verify_csrf = AsyncMock(return_value=False)

    service = MagicMock()
    service.record_attendance = AsyncMock()

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


def payload(status="present"):
    return {
        "student_id": str(ObjectId()),
        "status": status,
        "notes": None,
    }


def authenticate(client, auth, role="teacher"):
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": role,
    }
    client.cookies.set("quran_session", "session")


def test_attendance_requires_authentication(setup):
    client, auth, service = setup

    response = client.put(endpoint(), json=payload())

    assert response.status_code == 401
    service.record_attendance.assert_not_awaited()


def test_attendance_requires_csrf(setup):
    client, auth, service = setup
    authenticate(client, auth)

    response = client.put(endpoint(), json=payload())

    assert response.status_code == 403
    service.record_attendance.assert_not_awaited()


def test_attendance_success(setup):
    client, auth, service = setup
    authenticate(client, auth)
    auth.verify_csrf.return_value = True

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
    service.record_attendance.return_value = document

    response = client.put(
        endpoint(),
        json=payload(),
        headers={"X-CSRF-Token": "valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "present"
    assert response.json()["id"] == str(document["_id"])
    service.record_attendance.assert_awaited_once()


def test_attendance_rejects_invalid_status(setup):
    client, auth, service = setup
    authenticate(client, auth)
    auth.verify_csrf.return_value = True

    response = client.put(
        endpoint(),
        json=payload("unknown"),
        headers={"X-CSRF-Token": "valid-token"},
    )

    assert response.status_code == 422
    service.record_attendance.assert_not_awaited()


def test_attendance_forbidden_actor(setup):
    client, auth, service = setup
    authenticate(client, auth, role="student")
    auth.verify_csrf.return_value = True

    service.record_attendance.side_effect = HTTPException(
        status_code=403,
        detail="Not allowed to manage this Halaqa",
    )

    response = client.put(
        endpoint(),
        json=payload(),
        headers={"X-CSRF-Token": "valid-token"},
    )

    assert response.status_code == 403
    service.record_attendance.assert_awaited_once()
