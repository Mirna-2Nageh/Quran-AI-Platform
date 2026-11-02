"""Halaqat schema validation tests."""

import pytest
from app.schemas.halaqat import (
    EnrollmentCreate,
    HalaqaCreate,
    HalaqaUpdate,
)
from pydantic import ValidationError


def test_create_halaqa_valid():
    payload = HalaqaCreate(
        name="Hifz Beginners",
        teacher_id="507f1f77bcf86cd799439011",
    )
    assert payload.name == "Hifz Beginners"


def test_halaqa_name_too_short():
    with pytest.raises(ValidationError):
        HalaqaCreate(
            name="AB",
            teacher_id="507f1f77bcf86cd799439011",
        )


def test_halaqa_invalid_status():
    with pytest.raises(ValidationError):
        HalaqaUpdate(status="deleted")


def test_enrollment_requires_student():
    with pytest.raises(ValidationError):
        EnrollmentCreate()


def test_halaqa_description_limit():
    with pytest.raises(ValidationError):
        HalaqaCreate(
            name="Beginners",
            teacher_id="507f1f77bcf86cd799439011",
            description="x" * 1001,
        )
