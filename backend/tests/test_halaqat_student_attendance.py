"""Student attendance history authorization tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.halaqat import HalaqatService
from bson import ObjectId
from fastapi import HTTPException


def make_service():
    service = HalaqatService({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })
    service.repository.list_student_attendance = AsyncMock(
        return_value=[{"status": "present"}]
    )
    return service


def test_student_reads_own_attendance():
    service = make_service()
    student_id = ObjectId()
    actor = {"_id": student_id, "role": "student"}

    result = asyncio.run(
        service.list_my_attendance(actor=actor)
    )

    assert result == [{"status": "present"}]
    service.repository.list_student_attendance.assert_awaited_once_with(
        str(student_id)
    )


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_non_student_cannot_use_student_history(role):
    service = make_service()
    actor = {"_id": ObjectId(), "role": role}

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.list_my_attendance(actor=actor))

    assert exc.value.status_code == 403
    service.repository.list_student_attendance.assert_not_awaited()
