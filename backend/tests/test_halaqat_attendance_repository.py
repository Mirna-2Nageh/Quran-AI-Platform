"""Attendance repository tests."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.repositories.halaqat import HalaqatRepository
from bson import ObjectId
from pymongo.errors import DuplicateKeyError


def make_repo():
    sessions = MagicMock()
    enrollments = MagicMock()
    attendance = MagicMock()

    repo = HalaqatRepository({
        "halaqat": MagicMock(),
        "halaqa_enrollments": enrollments,
        "halaqa_sessions": sessions,
        "halaqa_attendance": attendance,
        "users": MagicMock(),
    })
    return repo, sessions, enrollments, attendance


def test_get_session():
    repo, sessions, _, _ = make_repo()
    session_id = ObjectId()
    document = {"_id": session_id}
    sessions.find_one = AsyncMock(return_value=document)

    result = asyncio.run(repo.get_session(str(session_id)))

    assert result == document
    sessions.find_one.assert_awaited_once_with({
        "_id": session_id
    })


def test_get_session_invalid_id():
    repo, sessions, _, _ = make_repo()

    result = asyncio.run(repo.get_session("invalid"))

    assert result is None
    sessions.find_one.assert_not_called()


def test_get_active_enrollment():
    repo, _, enrollments, _ = make_repo()
    halaqa_id = ObjectId()
    student_id = ObjectId()
    document = {"status": "active"}
    enrollments.find_one = AsyncMock(return_value=document)

    result = asyncio.run(repo.get_active_enrollment(
        str(halaqa_id), str(student_id)
    ))

    assert result == document
    enrollments.find_one.assert_awaited_once_with({
        "halaqa_id": halaqa_id,
        "student_id": student_id,
        "status": "active",
    })


def test_get_active_enrollment_invalid_id():
    repo, _, enrollments, _ = make_repo()

    result = asyncio.run(repo.get_active_enrollment(
        "invalid", str(ObjectId())
    ))

    assert result is None
    enrollments.find_one.assert_not_called()


def test_upsert_attendance():
    repo, _, _, attendance = make_repo()
    session_id = ObjectId()
    student_id = ObjectId()
    teacher_id = ObjectId()
    attendance.update_one = AsyncMock(
        return_value=SimpleNamespace()
    )
    attendance.find_one = AsyncMock(
        return_value={"status": "present"}
    )

    result = asyncio.run(repo.upsert_attendance(
        session_id=str(session_id),
        student_id=str(student_id),
        status="present",
        notes=None,
        recorded_by=str(teacher_id),
    ))

    assert result["status"] == "present"
    args, kwargs = attendance.update_one.await_args

    assert args[0] == {
        "session_id": session_id,
        "student_id": student_id,
    }
    assert kwargs["upsert"] is True
    assert args[1]["$set"]["recorded_by"] == teacher_id
    assert "created_at" in args[1]["$setOnInsert"]
    assert "created_at" not in args[1]["$set"]


def test_upsert_handles_duplicate_key():
    repo, _, _, attendance = make_repo()
    attendance.update_one = AsyncMock(
        side_effect=[
            DuplicateKeyError("duplicate"),
            SimpleNamespace(),
        ]
    )
    attendance.find_one = AsyncMock(
        return_value={"status": "late"}
    )

    result = asyncio.run(repo.upsert_attendance(
        session_id=str(ObjectId()),
        student_id=str(ObjectId()),
        status="late",
        notes=None,
        recorded_by=str(ObjectId()),
    ))

    assert result["status"] == "late"
    assert attendance.update_one.await_count == 2

    retry_args, retry_kwargs = attendance.update_one.await_args
    assert "$setOnInsert" not in retry_args[1]
    assert retry_kwargs.get("upsert", False) is False
