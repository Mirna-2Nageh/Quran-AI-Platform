"""Attendance reading authorization tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.halaqat import HalaqatService
from bson import ObjectId
from fastapi import HTTPException


def make_service(*, role="teacher", owner=True, exists=True):
    actor_id = ObjectId()
    halaqa_id = ObjectId()
    session_id = ObjectId()

    service = HalaqatService({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })

    actor = {"_id": actor_id, "role": role}

    service.repository.get_session = AsyncMock(
        return_value={
            "_id": session_id,
            "halaqa_id": halaqa_id,
        } if exists else None
    )

    service.repository.get_halaqa = AsyncMock(
        return_value={
            "_id": halaqa_id,
            "teacher_id": actor_id if owner else ObjectId(),
        }
    )

    service.repository.list_session_attendance = AsyncMock(
        return_value=[{"status": "present"}]
    )

    return service, actor, str(session_id)


def read(service, actor, session_id):
    return asyncio.run(service.list_session_attendance(
        actor=actor,
        session_id=session_id,
    ))


@pytest.mark.parametrize(
    ("role", "owner"),
    [
        ("teacher", True),
        ("admin", False),
    ],
)
def test_authorized_read(role, owner):
    service, actor, session_id = make_service(
        role=role,
        owner=owner,
    )

    result = read(service, actor, session_id)

    assert result == [{"status": "present"}]
    service.repository.list_session_attendance.assert_awaited_once_with(
        session_id
    )


@pytest.mark.parametrize(
    ("role", "owner"),
    [
        ("student", True),
        ("teacher", False),
    ],
)
def test_unauthorized_read(role, owner):
    service, actor, session_id = make_service(
        role=role,
        owner=owner,
    )

    with pytest.raises(HTTPException) as exc:
        read(service, actor, session_id)

    assert exc.value.status_code == 403
    service.repository.list_session_attendance.assert_not_awaited()


def test_missing_session():
    service, actor, session_id = make_service(exists=False)

    with pytest.raises(HTTPException) as exc:
        read(service, actor, session_id)

    assert exc.value.status_code == 404
    service.repository.list_session_attendance.assert_not_awaited()


def test_invalid_session_id():
    service, actor, _ = make_service()

    with pytest.raises(HTTPException) as exc:
        read(service, actor, "invalid")

    assert exc.value.status_code == 422
    service.repository.get_session.assert_not_awaited()
