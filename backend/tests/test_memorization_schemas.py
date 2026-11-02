
"""Validation tests for memorization API schemas."""

import pytest
from app.schemas.memorization import (
    MemorizationPlanCreate,
    MemorizationPlanUpdate,
    MemorizationSessionCreate,
)
from pydantic import ValidationError


def test_valid_memorization_plan():
    plan = MemorizationPlanCreate(
        surah_number=2,
        start_ayah=1,
        end_ayah=20,
    )
    assert plan.surah_number == 2
    assert plan.end_ayah == 20


@pytest.mark.parametrize(
    "values",
    [
        {"surah_number": 0, "start_ayah": 1, "end_ayah": 1},
        {"surah_number": 115, "start_ayah": 1, "end_ayah": 1},
        {"surah_number": 1, "start_ayah": 0, "end_ayah": 1},
        {"surah_number": 1, "start_ayah": 5, "end_ayah": 2},
    ],
)
def test_invalid_memorization_plan(values):
    with pytest.raises(ValidationError):
        MemorizationPlanCreate(**values)


def test_plan_status_validation():
    assert MemorizationPlanUpdate(status="paused").status == "paused"

    with pytest.raises(ValidationError):
        MemorizationPlanUpdate(status="unknown")


def test_session_validation():
    session = MemorizationSessionCreate(
        session_type="revision",
        result="needs_review",
        notes="Revise these verses tomorrow",
    )
    assert session.session_type == "revision"


@pytest.mark.parametrize(
    "values",
    [
        {"session_type": "unknown", "result": "completed"},
        {"session_type": "revision", "result": "excellent"},
        {
            "session_type": "revision",
            "result": "completed",
            "notes": "x" * 1001,
        },
    ],
)
def test_invalid_memorization_session(values):
    with pytest.raises(ValidationError):
        MemorizationSessionCreate(**values)
