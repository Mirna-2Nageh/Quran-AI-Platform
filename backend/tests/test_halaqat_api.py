"""HTTP security tests for Halaqat endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.v1.auth import get_auth_service
from app.api.v1.halaqat import get_service
from app.main import app
from bson import ObjectId
from fastapi.testclient import TestClient


@pytest.fixture
def client_setup():
    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)
    auth.verify_csrf = AsyncMock(return_value=False)

    service = MagicMock()
    service.create_halaqa = AsyncMock()
    service.get_managed_halaqa = AsyncMock()
    service.enroll_student = AsyncMock()
    service.list_enrollments = AsyncMock()

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: service

    try:
        with TestClient(app) as client:
            yield client, auth, service
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def test_create_requires_authentication(client_setup):
    client, auth, service = client_setup

    response = client.post(
        "/api/v1/halaqat",
        json={"name": "Beginners", "teacher_id": str(ObjectId())},
    )

    assert response.status_code == 401
    service.create_halaqa.assert_not_awaited()


def test_create_requires_csrf(client_setup):
    client, auth, service = client_setup
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "admin",
    }

    client.cookies.set("quran_session", "session")

    response = client.post(
        "/api/v1/halaqat",
        json={"name": "Beginners", "teacher_id": str(ObjectId())},
    )

    assert response.status_code == 403
    service.create_halaqa.assert_not_awaited()


def test_get_halaqa_requires_authentication(client_setup):
    client, auth, service = client_setup

    response = client.get(f"/api/v1/halaqat/{ObjectId()}")

    assert response.status_code == 401
    service.get_managed_halaqa.assert_not_awaited()


def test_enrollment_requires_authentication(client_setup):
    client, auth, service = client_setup

    response = client.post(
        f"/api/v1/halaqat/{ObjectId()}/enrollments",
        json={"student_id": str(ObjectId())},
    )

    assert response.status_code == 401
    service.enroll_student.assert_not_awaited()


def test_enrollment_requires_csrf(client_setup):
    client, auth, service = client_setup
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "teacher",
    }

    client.cookies.set("quran_session", "session")

    response = client.post(
        f"/api/v1/halaqat/{ObjectId()}/enrollments",
        json={"student_id": str(ObjectId())},
    )

    assert response.status_code == 403
    service.enroll_student.assert_not_awaited()


def test_my_halaqat_rejects_student(client_setup):
    client, auth, service = client_setup
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "student",
    }

    response = client.get("/api/v1/halaqat/my")

    assert response.status_code == 403
    service.repository.list_teacher_halaqat.assert_not_called()


def test_my_halaqat_requires_authentication(client_setup):
    client, auth, service = client_setup

    response = client.get("/api/v1/halaqat/my")

    assert response.status_code == 401


def test_list_enrollments_requires_authentication(client_setup):
    client, auth, service = client_setup

    response = client.get(
        f"/api/v1/halaqat/{ObjectId()}/enrollments"
    )

    assert response.status_code == 401
    service.list_enrollments.assert_not_awaited()


def test_teacher_cannot_read_other_teacher_halaqa():
    from app.services.halaqat import HalaqatService

    teacher_id = ObjectId()
    other_teacher_id = ObjectId()
    halaqa_id = ObjectId()

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value={
        "_id": teacher_id,
        "role": "teacher",
        "is_active": True,
    })

    service = HalaqatService({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })
    service.repository.get_halaqa = AsyncMock(return_value={
        "_id": halaqa_id,
        "teacher_id": other_teacher_id,
    })

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/halaqat/{halaqa_id}")

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "Not allowed to manage this Halaqa"
        )
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def test_teacher_cannot_enroll_into_other_halaqa():
    from app.services.halaqat import HalaqatService

    teacher_id = ObjectId()
    halaqa_id = ObjectId()

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value={
        "_id": teacher_id,
        "role": "teacher",
        "is_active": True,
    })
    auth.verify_csrf = AsyncMock(return_value=True)

    service = HalaqatService({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })
    service.repository.get_halaqa = AsyncMock(return_value={
        "_id": halaqa_id,
        "teacher_id": ObjectId(),
    })
    service.users.get_by_id = AsyncMock()

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: service

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "session")
            response = client.post(
                f"/api/v1/halaqat/{halaqa_id}/enrollments",
                headers={"X-CSRF-Token": "valid"},
                json={"student_id": str(ObjectId())},
            )

        assert response.status_code == 403
        service.users.get_by_id.assert_not_awaited()
        auth.verify_csrf.assert_awaited_once_with("session", "valid")
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def test_my_enrollments_rejects_teacher(client_setup):
    client, auth, service = client_setup
    auth.get_current_user.return_value = {
        "_id": ObjectId(),
        "role": "teacher",
        "is_active": True,
    }

    from fastapi import HTTPException

    service.list_my_enrollments = AsyncMock(
        side_effect=HTTPException(
            status_code=403,
            detail="Student required",
        )
    )

    response = client.get("/api/v1/halaqat/my/enrollments")

    assert response.status_code == 403


def test_my_enrollments_requires_authentication(client_setup):
    client, auth, service = client_setup

    response = client.get("/api/v1/halaqat/my/enrollments")

    assert response.status_code == 401


def test_student_membership_http_with_real_service():
    from app.services.halaqat import HalaqatService

    student_id = ObjectId()
    enrollment_id = ObjectId()
    halaqa_id = ObjectId()

    from datetime import datetime, timezone

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value={
        "_id": student_id,
        "role": "student",
        "is_active": True,
    })

    service = HalaqatService({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })

    service.repository.list_student_enrollments = AsyncMock(
        return_value=[{
            "_id": enrollment_id,
            "halaqa_id": halaqa_id,
            "student_id": student_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
        }]
    )

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/halaqat/my/enrollments"
            )

        assert response.status_code == 200
        assert response.json()[0]["student_id"] == str(student_id)
        service.repository.list_student_enrollments.assert_awaited_once_with(
            str(student_id)
        )
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def test_create_session_requires_authentication():
    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: MagicMock()
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/halaqat/{ObjectId()}/sessions",
                json={
                    "scheduled_at": "2030-01-01T10:00:00Z",
                    "duration_minutes": 60,
                },
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def test_list_sessions_requires_authentication():
    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: MagicMock()
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/halaqat/{ObjectId()}/sessions"
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def test_create_session_requires_csrf():
    auth = MagicMock()
    auth.verify_csrf = AsyncMock(return_value=False)
    auth.get_current_user = AsyncMock(return_value={
        "_id": ObjectId(),
        "role": "teacher",
        "is_active": True,
    })

    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_service] = lambda: MagicMock()
    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "session")
            response = client.post(
                f"/api/v1/halaqat/{ObjectId()}/sessions",
                json={
                    "scheduled_at": "2030-01-01T10:00:00Z",
                    "duration_minutes": 60,
                },
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_service, None)


def test_create_session_success(client_setup):
    from datetime import datetime, timezone

    client, auth, service = client_setup
    teacher_id = ObjectId()
    halaqa_id = ObjectId()
    session_id = ObjectId()
    now = datetime.now(timezone.utc)
    scheduled = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)

    auth.get_current_user.return_value = {
        "_id": teacher_id,
        "role": "teacher",
        "is_active": True,
    }
    auth.verify_csrf.return_value = True

    service.create_session = AsyncMock(return_value={
        "_id": session_id,
        "halaqa_id": halaqa_id,
        "scheduled_at": scheduled,
        "duration_minutes": 60,
        "notes": "Revision",
        "status": "scheduled",
        "created_at": now,
        "updated_at": now,
    })

    client.cookies.set("quran_session", "session")

    response = client.post(
        f"/api/v1/halaqat/{halaqa_id}/sessions",
        headers={"X-CSRF-Token": "valid"},
        json={
            "scheduled_at": "2030-01-01T12:00:00+02:00",
            "duration_minutes": 60,
            "notes": "Revision",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(session_id)
    assert response.json()["status"] == "scheduled"
    assert response.json()["duration_minutes"] == 60

    auth.verify_csrf.assert_awaited_once_with("session", "valid")
    service.create_session.assert_awaited_once()
    kwargs = service.create_session.await_args.kwargs
    assert kwargs["halaqa_id"] == str(halaqa_id)
    assert kwargs["actor"]["_id"] == teacher_id
    assert kwargs["scheduled_at"].utcoffset().total_seconds() == 7200


def test_list_sessions_success(client_setup):
    from datetime import datetime, timezone

    client, auth, service = client_setup
    teacher_id = ObjectId()
    halaqa_id = ObjectId()
    session_id = ObjectId()
    now = datetime.now(timezone.utc)

    auth.get_current_user.return_value = {
        "_id": teacher_id,
        "role": "teacher",
        "is_active": True,
    }

    service.list_sessions = AsyncMock(return_value=[{
        "_id": session_id,
        "halaqa_id": halaqa_id,
        "scheduled_at": now,
        "duration_minutes": 45,
        "notes": None,
        "status": "scheduled",
        "created_at": now,
        "updated_at": now,
    }])

    response = client.get(
        f"/api/v1/halaqat/{halaqa_id}/sessions"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(session_id)
    assert data[0]["duration_minutes"] == 45
    service.list_sessions.assert_awaited_once()
