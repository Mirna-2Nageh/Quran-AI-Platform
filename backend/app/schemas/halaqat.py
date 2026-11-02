"""Halaqat API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

HalaqaStatus = Literal["active", "paused", "completed"]
EnrollmentStatus = Literal["active", "withdrawn"]


class HalaqaCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    teacher_id: str


class HalaqaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    teacher_id: str | None = None
    status: HalaqaStatus | None = None


class HalaqaResponse(BaseModel):
    id: str
    name: str
    description: str | None
    teacher_id: str
    status: HalaqaStatus
    created_at: datetime
    updated_at: datetime


class EnrollmentCreate(BaseModel):
    student_id: str


class EnrollmentResponse(BaseModel):
    id: str
    halaqa_id: str
    student_id: str
    student_name: str | None = None
    halaqa_name: str | None = None
    status: EnrollmentStatus
    created_at: datetime


SessionStatus = Literal["scheduled", "completed", "cancelled"]


class HalaqaSessionCreate(BaseModel):
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=240)
    notes: str | None = Field(default=None, max_length=1000)


class HalaqaSessionResponse(BaseModel):
    id: str
    halaqa_id: str
    scheduled_at: datetime
    duration_minutes: int
    notes: str | None
    status: SessionStatus
    created_at: datetime
    updated_at: datetime


# Attendance Management V1

AttendanceStatus = Literal[
    "present", "absent", "late", "excused"
]


class AttendanceRecordCreate(BaseModel):
    student_id: str
    status: AttendanceStatus
    notes: str | None = Field(default=None, max_length=1000)


class AttendanceRecordResponse(BaseModel):
    halaqa_name: str | None = None
    session_scheduled_at: datetime | None = None
    id: str
    session_id: str
    student_id: str
    status: AttendanceStatus
    notes: str | None
    recorded_by: str
    created_at: datetime
    updated_at: datetime
