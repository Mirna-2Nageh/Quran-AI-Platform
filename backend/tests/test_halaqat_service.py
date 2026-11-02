"""Tests for Halaqat service permissions."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.services.halaqat import HalaqatService
from bson import ObjectId
from fastapi import HTTPException


def make_service():
    service = HalaqatService({
        "halaqat": None,
        "halaqa_enrollments": None,
        "halaqa_sessions": None,
        "halaqa_attendance": None,
        "users": None,
    })
    service.repository.get_halaqa = AsyncMock()
    service.repository.create_halaqa = AsyncMock()
    service.repository.enroll_student = AsyncMock()
    service.repository.list_enrollments = AsyncMock()
    service.users.get_by_id = AsyncMock()
    return service


def test_only_admin_can_create_halaqa():
    service = make_service()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.create_halaqa(
            actor={"role": "teacher"},
            name="Beginners",
            description=None,
            teacher_id=str(ObjectId()),
        ))

    assert exc.value.status_code == 403
    service.users.get_by_id.assert_not_awaited()


def test_create_halaqa_rejects_non_teacher():
    service = make_service()
    service.users.get_by_id.return_value = {
        "role": "student",
        "is_active": True,
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.create_halaqa(
            actor={"role": "admin"},
            name="Beginners",
            description=None,
            teacher_id=str(ObjectId()),
        ))

    assert exc.value.status_code == 422
    service.repository.create_halaqa.assert_not_awaited()


def test_admin_creates_halaqa_with_active_teacher():
    service = make_service()
    service.users.get_by_id.return_value = {
        "role": "teacher",
        "is_active": True,
    }
    service.repository.create_halaqa.return_value = {
        "name": "Beginners",
    }

    result = asyncio.run(service.create_halaqa(
        actor={"role": "admin"},
        name="Beginners",
        description=None,
        teacher_id=str(ObjectId()),
    ))

    assert result["name"] == "Beginners"
    service.repository.create_halaqa.assert_awaited_once()


def test_teacher_cannot_manage_other_halaqa():
    service = make_service()
    service.repository.get_halaqa.return_value = {
        "teacher_id": ObjectId(),
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.get_managed_halaqa(
            actor={"role": "teacher", "_id": ObjectId()},
            halaqa_id=str(ObjectId()),
        ))

    assert exc.value.status_code == 403


def test_teacher_can_manage_own_halaqa():
    service = make_service()
    teacher_id = ObjectId()
    service.repository.get_halaqa.return_value = {
        "teacher_id": teacher_id,
    }

    result = asyncio.run(service.get_managed_halaqa(
        actor={"role": "teacher", "_id": teacher_id},
        halaqa_id=str(ObjectId()),
    ))

    assert result["teacher_id"] == teacher_id


def test_enrollment_rejects_inactive_student():
    service = make_service()
    service.repository.get_halaqa.return_value = {
        "teacher_id": ObjectId(),
    }
    service.users.get_by_id.return_value = {
        "role": "student",
        "is_active": False,
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.enroll_student(
            actor={"role": "admin"},
            halaqa_id=str(ObjectId()),
            student_id=str(ObjectId()),
        ))

    assert exc.value.status_code == 422
    service.repository.enroll_student.assert_not_awaited()


def test_enrollment_rejects_student_actor():
    service = make_service()
    service.repository.get_halaqa.return_value = {
        "teacher_id": ObjectId(),
    }

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.enroll_student(
            actor={"role": "student", "_id": ObjectId()},
            halaqa_id=str(ObjectId()),
            student_id=str(ObjectId()),
        ))

    assert exc.value.status_code == 403
    service.users.get_by_id.assert_not_awaited()


def test_student_can_list_own_enrollments():
    service = make_service()
    student_id = ObjectId()
    expected = [{"student_id": student_id, "status": "active"}]
    service.repository.list_student_enrollments = AsyncMock(
        return_value=expected
    )

    result = asyncio.run(service.list_my_enrollments(
        actor={"_id": student_id, "role": "student"},
    ))

    assert result == expected
    service.repository.list_student_enrollments.assert_awaited_once_with(
        str(student_id)
    )


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_non_student_cannot_list_student_enrollments(role):
    service = make_service()
    service.repository.list_student_enrollments = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.list_my_enrollments(
            actor={"_id": ObjectId(), "role": role},
        ))

    assert exc.value.status_code == 403
    service.repository.list_student_enrollments.assert_not_awaited()
