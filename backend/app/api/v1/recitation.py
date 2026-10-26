from fastapi import APIRouter

from app.ai.alignment import align_words
from app.schemas.recitation import (
    AlignmentIssueResponse,
    AlignmentRequest,
    AlignmentResponse,
)

router = APIRouter(prefix="/recitation", tags=["Recitation"])


@router.post("/align", response_model=AlignmentResponse)
def align_recitation(payload: AlignmentRequest) -> AlignmentResponse:
    """Compare recognized text against the expected Quran text."""
    result = align_words(
        expected_text=payload.expected_text,
        recognized_text=payload.recognized_text,
    )

    return AlignmentResponse(
        expected_word_count=result.expected_word_count,
        recognized_word_count=result.recognized_word_count,
        matched_word_count=result.matched_word_count,
        issues=[
            AlignmentIssueResponse(
                operation=issue.operation,
                expected_word=issue.expected_word,
                recognized_word=issue.recognized_word,
                expected_index=issue.expected_index,
                recognized_index=issue.recognized_index,
            )
            for issue in result.issues
        ],
    )
