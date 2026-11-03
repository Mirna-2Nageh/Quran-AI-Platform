
"""API schemas for memorization plans and practice sessions."""

from datetime import datetime
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator

PlanStatus = Literal["active", "completed", "paused"]
SessionType = Literal["memorization", "revision"]
SessionResult = Literal["completed", "needs_review", "incomplete"]


class MemorizationPlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surah_number: int = Field(ge=1, le=114)
    start_ayah: int = Field(ge=1)
    end_ayah: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_ayah < self.start_ayah:
            raise ValueError("end_ayah must be >= start_ayah")
        return self


class MemorizationPlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: PlanStatus


class MemorizationPlanResponse(BaseModel):
    id: str
    surah_number: int
    start_ayah: int
    end_ayah: int
    status: PlanStatus
    created_at: datetime
    updated_at: datetime


class MemorizationSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_type: SessionType
    result: SessionResult
    notes: str | None = Field(default=None, max_length=1000)
    recitation_session_id: str | None = None

    @model_validator(mode="after")
    def validate_recitation_session_id(self):
        if (
            self.recitation_session_id is not None
            and not ObjectId.is_valid(self.recitation_session_id)
        ):
            raise ValueError("Invalid recitation session ID")
        return self


class MemorizationSessionResponse(BaseModel):
    id: str
    plan_id: str
    session_type: SessionType
    result: SessionResult
    notes: str | None
    completed_at: datetime
    recitation_session_id: str | None = None


class MemorizationProgressResponse(BaseModel):
    total_plans: int = Field(ge=0)
    completed_plans: int = Field(ge=0)
    unique_planned_ayahs: int = Field(ge=0)
    completed_ayahs: int = Field(ge=0)
    completion_rate: float = Field(ge=0, le=100)
    revision_sessions: int = Field(ge=0)
