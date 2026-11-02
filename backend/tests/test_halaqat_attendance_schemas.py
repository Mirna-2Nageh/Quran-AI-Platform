"""Attendance schema validation tests."""

import pytest
from app.schemas.halaqat import AttendanceRecordCreate
from bson import ObjectId
from pydantic import ValidationError


@pytest.mark.parametrize(
    "status",
    ["present", "absent", "late", "excused"],
)
def test_valid_attendance_status(status):
    record = AttendanceRecordCreate(
        student_id=str(ObjectId()),
        status=status,
    )
    assert record.status == status


def test_invalid_attendance_status():
    with pytest.raises(ValidationError):
        AttendanceRecordCreate(
            student_id=str(ObjectId()),
            status="unknown",
        )


def test_attendance_notes_length_limit():
    with pytest.raises(ValidationError):
        AttendanceRecordCreate(
            student_id=str(ObjectId()),
            status="present",
            notes="x" * 1001,
        )
