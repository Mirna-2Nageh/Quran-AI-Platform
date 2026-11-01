"""Contract tests for recitation API response schemas."""

from datetime import datetime, timezone

import pytest
from app.main import app
from app.schemas.recitation_api import (
    RecitationAnalysisResponse,
    RecitationHistoryResponse,
    WordTimingResponse,
)
from pydantic import ValidationError


def test_analyze_openapi_response_contract():
    schema = app.openapi()

    response = schema["paths"][
        "/api/v1/recitation/analyze"
    ]["post"]["responses"]["200"]

    assert response["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RecitationAnalysisResponse"
    )


def test_history_openapi_response_contract():
    schema = app.openapi()

    response = schema["paths"][
        "/api/v1/recitation/history"
    ]["get"]["responses"]["200"]

    assert response["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RecitationHistoryResponse"
    )


def test_word_timing_contract():
    timing = WordTimingResponse(
        word="الله",
        start_seconds=0.5,
        end_seconds=None,
        timing_type="estimated_asr_word_boundary",
    )

    assert timing.end_seconds is None

    with pytest.raises(ValidationError):
        WordTimingResponse(
            word="الله",
            start_seconds=-1,
            timing_type="estimated_asr_word_boundary",
        )


def test_history_legacy_alignment_contract():
    response = RecitationHistoryResponse.model_validate(
        {
            "items": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "surah_number": 1,
                    "ayah_number": 1,
                    "end_ayah_number": 1,
                    "expected_text": "بسم الله",
                    "recognized_text": "بسم الله",
                    "alignment": {"issues": []},
                    "analysis_type": "word_level_asr_alignment",
                    "tajweed_analyzed": False,
                    "created_at": datetime.now(timezone.utc),
                }
            ],
            "count": 1,
        }
    )

    assert response.count == 1
    assert response.items[0].alignment == {"issues": []}


def test_analysis_requires_alignment_contract():
    with pytest.raises(ValidationError):
        RecitationAnalysisResponse.model_validate(
            {
                "session_id": "test-session",
                "recognized_text": "بسم الله",
                "alignment": {"issues": []},
                "word_timings": [],
                "analysis_type": "word_level_asr_alignment",
                "tajweed_analyzed": False,
            }
        )
