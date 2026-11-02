"""HTTP tests for student attendance history."""

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
    service.list_my_attendance = AsyncMock(return_value=[])

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: service

    try:
        with TestClient(app) as client:
            yield client, auth, service
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


URL = "/api/v1/halaqat/my/attendance"


def test_history_requires_authentication(setup):
    client, auth, service = setup

    response = client.get(URL)

    assert response.status_code == 401
    service.list_my_attendance.assert_not_awaited()


def test_student_reads_attendance_history(setup):
    client, auth, service = setup
    student_id = ObjectId()

    auth.get_current_user.return_value = {
        "_id": student_id,
        "role": "student",
    }

    now = datetime.now(timezone.utc)
    document = {
        "_id": ObjectId(),
        "session_id": ObjectId(),
        "student_id": student_id,
        "status": "present",
        "notes": None,
        "recorded_by": ObjectId(),
        "created_at": now,
        "updated_at": now,
    }
    service.list_my_attendance.return_value = [document]

    response = client.get(URL)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["student_id"] == str(student_id)
    assert response.json()[0]["status"] == "present"

    service.list_my_attendance.assert_awaited_once()
    assert (
        service.list_my_attendance.await_args.kwargs["actor"]["_id"]
        == student_id
    )


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_non_student_history_forbidden(setup, role):
    client, auth, service = setup

    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": role,
    }

    service.list_my_attendance.side_effect = HTTPException(
        status_code=403,
        detail="Student required",
    )

    response = client.get(URL)

    assert response.status_code == 403
    service.list_my_attendance.assert_awaited_once()
