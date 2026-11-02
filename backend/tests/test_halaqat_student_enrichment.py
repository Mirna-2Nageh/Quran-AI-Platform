"""Regression tests for student Halaqat display metadata."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.repositories.halaqat import HalaqatRepository
from bson import ObjectId


def cursor_with(documents):
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=documents)
    return cursor


def test_student_enrollments_include_halaqa_name():
    student_id, halaqa_id = ObjectId(), ObjectId()
    db = {
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    }
    db["halaqa_enrollments"].find.return_value = cursor_with([
        {"student_id": student_id, "halaqa_id": halaqa_id}
    ])
    db["halaqat"].find.return_value = cursor_with([
        {"_id": halaqa_id, "name": "fisst"}
    ])

    repo = HalaqatRepository(db)
    result = asyncio.run(repo.list_student_enrollments(str(student_id)))

    assert result[0]["halaqa_name"] == "fisst"
    db["halaqat"].find.assert_called_once_with(
        {"_id": {"$in": [halaqa_id]}},
        {"name": 1},
    )


def test_student_attendance_includes_session_details():
    student_id, session_id, halaqa_id = (
        ObjectId(), ObjectId(), ObjectId()
    )
    scheduled_at = datetime(2026, 11, 2, 17, 5, tzinfo=timezone.utc)
    db = {
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    }

    db["halaqa_attendance"].find.return_value = cursor_with([
        {"student_id": student_id, "session_id": session_id}
    ])
    db["halaqa_sessions"].find.return_value = cursor_with([
        {
            "_id": session_id,
            "halaqa_id": halaqa_id,
            "scheduled_at": scheduled_at,
        }
    ])
    db["halaqat"].find.return_value = cursor_with([
        {"_id": halaqa_id, "name": "fisst"}
    ])

    repo = HalaqatRepository(db)
    result = asyncio.run(repo.list_student_attendance(str(student_id)))

    assert result[0]["halaqa_name"] == "fisst"
    assert result[0]["session_scheduled_at"] == scheduled_at
    db["halaqa_attendance"].find.assert_called_once_with(
        {"student_id": student_id}
    )


def test_empty_student_history_skips_lookups():
    student_id = ObjectId()
    db = {
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    }
    db["halaqa_attendance"].find.return_value = cursor_with([])

    repo = HalaqatRepository(db)
    result = asyncio.run(repo.list_student_attendance(str(student_id)))

    assert result == []
    db["halaqa_sessions"].find.assert_not_called()
    db["halaqat"].find.assert_not_called()
