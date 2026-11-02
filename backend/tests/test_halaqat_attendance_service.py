"""Attendance business rules and authorization tests."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.halaqat import HalaqatService
from bson import ObjectId
from fastapi import HTTPException


def make_service(
    *,
    role="teacher",
    owner=True,
    halaqa_status="active",
    session_status="scheduled",
    started=True,
    enrolled=True,
    session_exists=True,
):
    actor_id = ObjectId()
    halaqa_id = ObjectId()
    session_id = ObjectId()
    student_id = ObjectId()

    service = HalaqatService({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })

    actor = {
        "_id": actor_id,
        "role": role,
        "is_active": True,
    }

    when = datetime.now(timezone.utc) + timedelta(
        hours=-2 if started else 2
    )

    service.repository.get_session = AsyncMock(
        return_value={
            "_id": session_id,
            "halaqa_id": halaqa_id,
            "status": session_status,
            "scheduled_at": when,
        } if session_exists else None
    )

    service.repository.get_halaqa = AsyncMock(return_value={
        "_id": halaqa_id,
        "teacher_id": actor_id if owner else ObjectId(),
        "status": halaqa_status,
    })

    service.repository.get_active_enrollment = AsyncMock(
        return_value={"status": "active"} if enrolled else None
    )

    service.repository.upsert_attendance = AsyncMock(
        return_value={"status": "present"}
    )

    return service, actor, str(session_id), str(student_id)


def record(service, actor, session_id, student_id):
    return asyncio.run(service.record_attendance(
        actor=actor,
        session_id=session_id,
        student_id=student_id,
        status="present",
        notes=None,
    ))


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_authorized_actor_records_attendance(role):
    service, actor, session_id, student_id = make_service(
        role=role,
        owner=False if role == "admin" else True,
    )

    result = record(service, actor, session_id, student_id)

    assert result["status"] == "present"
    service.repository.upsert_attendance.assert_awaited_once()
    kwargs = service.repository.upsert_attendance.await_args.kwargs
    assert kwargs["recorded_by"] == str(actor["_id"])
    assert kwargs["student_id"] == student_id


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({"role": "student"}, 403),
        ({"owner": False}, 403),
        ({"halaqa_status": "paused"}, 409),
        ({"session_status": "cancelled"}, 409),
        ({"started": False}, 409),
        ({"enrolled": False}, 409),
        ({"session_exists": False}, 404),
    ],
)
def test_attendance_rejected(options, expected):
    service, actor, session_id, student_id = make_service(**options)

    with pytest.raises(HTTPException) as exc:
        record(service, actor, session_id, student_id)

    assert exc.value.status_code == expected
    service.repository.upsert_attendance.assert_not_awaited()


def test_attendance_rejects_invalid_session_id():
    service, actor, _, student_id = make_service()

    with pytest.raises(HTTPException) as exc:
        record(service, actor, "invalid", student_id)

    assert exc.value.status_code == 422
    service.repository.get_session.assert_not_awaited()


def test_attendance_rejects_invalid_student_id():
    service, actor, session_id, _ = make_service()

    with pytest.raises(HTTPException) as exc:
        record(service, actor, session_id, "invalid")

    assert exc.value.status_code == 422
    service.repository.upsert_attendance.assert_not_awaited()
