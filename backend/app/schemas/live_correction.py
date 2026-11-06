"""Response models for chunk-based memorization correction."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.recitation import AlignmentResponse


class WordFeedback(BaseModel):
    index: int = Field(ge=0)
    word: str
    status: Literal["matched", "review", "pending"]
    recognized_word: str | None = None


class LiveCorrectionResponse(BaseModel):
    surah_number: int = Field(ge=1, le=114)
    ayah_number: int = Field(ge=1)
    recognized_text: str
    alignment: AlignmentResponse
    word_feedback: list[WordFeedback]
    next_word_index: int = Field(ge=0)
    has_more_words: bool
    analysis_type: Literal["chunk_based_word_alignment"] = (
        "chunk_based_word_alignment"
    )
