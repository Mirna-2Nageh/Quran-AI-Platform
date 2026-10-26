from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

IssueType = Literal["substitution", "deletion", "insertion"]


class AlignmentRequest(BaseModel):
    """Input for comparing expected and recognized Quran text."""

    model_config = ConfigDict(extra="forbid")

    expected_text: str
    recognized_text: str

    @field_validator("expected_text")
    @classmethod
    def validate_expected_text(cls, value: str) -> str:
        """Reject an expected text containing only whitespace."""
        if not value.strip():
            raise ValueError("expected_text must contain at least one character")
        return value


class AlignmentIssueResponse(BaseModel):
    """A single word-level alignment difference."""

    operation: IssueType
    expected_word: str | None
    recognized_word: str | None
    expected_index: int | None
    recognized_index: int | None


class AlignmentResponse(BaseModel):
    """Result of comparing expected and recognized text."""

    expected_word_count: int
    recognized_word_count: int
    matched_word_count: int
    issues: list[AlignmentIssueResponse]
