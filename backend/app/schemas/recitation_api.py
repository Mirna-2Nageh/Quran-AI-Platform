"""Typed API responses for recitation analysis and history."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.recitation import AlignmentResponse


class WordTimingResponse(BaseModel):
    word: str
    start_seconds: float = Field(ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    timing_type: str


class RecitationAnalysisResponse(BaseModel):
    session_id: str
    recognized_text: str
    alignment: AlignmentResponse
    word_timings: list[WordTimingResponse]
    analysis_type: Literal["word_level_asr_alignment"]
    tajweed_analyzed: bool


class RecitationHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    surah_number: int
    ayah_number: int
    end_ayah_number: int
    expected_text: str
    recognized_text: str
    alignment: dict[str, Any]
    analysis_type: str
    tajweed_analyzed: bool
    created_at: datetime


class RecitationHistoryResponse(BaseModel):
    items: list[RecitationHistoryItem]
    count: int
    has_more: bool = False
    next_cursor: str | None = None
