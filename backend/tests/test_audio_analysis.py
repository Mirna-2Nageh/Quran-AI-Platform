"""Integration tests for authenticated Quran audio analysis."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import get_auth_service
from app.api.v1.audio_analysis import MAX_AUDIO_SIZE
from app.main import app
from app.services.quran_asr import ASRError, ASRMetadata
from app.services.quran_text import get_quran_text


WEBM = b"\x1a\x45\xdf\xa3" + b"test-audio-data"
EXPECTED = get_quran_text(1, 1, 1)


@pytest.fixture
def client():
    service = AsyncMock()
    service.get_current_user.return_value = {"_id": "test-user"}
    service.verify_csrf.return_value = True

    from bson import ObjectId
    from unittest.mock import MagicMock

    collection = MagicMock()
    collection.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId())
    )

    service.database = {
        "recitation_sessions": collection,
    }

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as http:
            http.cookies.set("quran_session", "test-session")
            yield http, service
    finally:
        app.dependency_overrides.clear()


def analyze(
    http,
    content=WEBM,
    content_type="audio/webm",
    expected_text=EXPECTED,
    headers=None,
):
    return http.post(
        "/api/v1/recitation/analyze",
        data={
            "expected_text": expected_text,
            "surah_number": 1,
            "ayah_number": 1,
        },
        files={
            "audio": ("recitation.webm", content, content_type),
        },
        headers={
            "X-CSRF-Token": "test-csrf",
            **(headers or {}),
        },
    )


def test_successful_analysis(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=ASRMetadata(text=EXPECTED, tokens=[], timestamps=[], timing_type="asr_character_token_timestamps"),
    ) as mock_asr:
        response = analyze(http)

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["recognized_text"] == EXPECTED
    assert data["alignment"]["matched_word_count"] == len(EXPECTED.split())
    assert data["alignment"]["issues"] == []
    assert data["tajweed_analyzed"] is False
    mock_asr.assert_awaited_once_with(WEBM)



def test_analysis_returns_word_timings(client):
    from app.ai.word_timing import WordTiming
    from app.services.quran_asr import ASRMetadata

    http, _ = client

    metadata = ASRMetadata(
        text=EXPECTED,
        tokens=[],
        timestamps=[],
        timing_type="asr_character_token_timestamps",
        word_timings=[
            WordTiming(
                word="بسم",
                start_seconds=0.12,
                end_seconds=0.68,
            ),
            WordTiming(
                word="الله",
                start_seconds=0.68,
                end_seconds=None,
            ),
        ],
    )

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=metadata,
        create=True,
    ) as mock_asr:
        response = analyze(http)

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["recognized_text"] == EXPECTED
    assert data["alignment"]["issues"] == []
    assert data["tajweed_analyzed"] is False
    assert data["word_timings"] == [
        {
            "word": "بسم",
            "start_seconds": 0.12,
            "end_seconds": 0.68,
            "timing_type": "estimated_asr_word_boundary",
        },
        {
            "word": "الله",
            "start_seconds": 0.68,
            "end_seconds": None,
            "timing_type": "estimated_asr_word_boundary",
        },
    ]

    mock_asr.assert_awaited_once_with(WEBM)


def test_analysis_succeeds_without_word_timings(client):
    from app.services.quran_asr import ASRMetadata

    http, _ = client

    metadata = ASRMetadata(
        text=EXPECTED,
        tokens=[],
        timestamps=[],
        timing_type="asr_character_token_timestamps",
        word_timings=[],
    )

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=metadata,
        create=True,
    ):
        response = analyze(http)

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["recognized_text"] == EXPECTED
    assert data["word_timings"] == []
    assert data["tajweed_analyzed"] is False


def test_missing_word_detected(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=ASRMetadata(text="بسم الله الرحيم", tokens=[], timestamps=[], timing_type="asr_character_token_timestamps"),
    ):
        response = analyze(http)

    assert response.status_code == 200, response.text

    issues = response.json()["alignment"]["issues"]

    assert any(
        issue["operation"] == "deletion"
        and issue["expected_word"] == EXPECTED.split()[2]
        for issue in issues
    )


def test_unauthenticated_rejected(client):
    http, service = client
    service.get_current_user.return_value = None

    response = analyze(http)

    assert response.status_code == 401


def test_invalid_csrf_rejected(client):
    http, service = client
    service.verify_csrf.return_value = False

    response = analyze(http)

    assert response.status_code == 403


def test_disallowed_origin_rejected(client):
    http, _ = client

    response = analyze(
        http,
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403


def test_empty_audio_rejected(client):
    http, _ = client

    response = analyze(http, content=b"")

    assert response.status_code == 400


def test_invalid_audio_signature_rejected(client):
    http, _ = client

    response = analyze(http, content=b"not-a-real-webm")

    assert response.status_code == 415


def test_unsupported_format_rejected(client):
    http, _ = client

    response = analyze(
        http,
        content=b"RIFF1234",
        content_type="audio/wav",
    )

    assert response.status_code == 415


def test_oversized_audio_rejected(client):
    http, _ = client

    response = analyze(
        http,
        content=b"\x1a\x45\xdf\xa3" + b"x" * MAX_AUDIO_SIZE,
    )

    assert response.status_code == 413


def test_empty_expected_text_rejected(client):
    http, _ = client

    response = analyze(http, expected_text="   ")

    assert response.status_code == 422


def test_empty_asr_transcription_rejected(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=ASRMetadata(text="", tokens=[], timestamps=[], timing_type="asr_character_token_timestamps"),
    ):
        response = analyze(http)

    assert response.status_code == 422


def test_asr_failure_returns_service_unavailable(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        side_effect=ASRError("Model unavailable"),
    ):
        response = analyze(http)

    assert response.status_code == 503
    assert "Model unavailable" not in response.text


def test_successful_analysis_saves_session(client):
    http, service = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=ASRMetadata(text=EXPECTED, tokens=[], timestamps=[], timing_type="asr_character_token_timestamps"),
    ), patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:

        repository = repository_class.return_value
        repository.create = AsyncMock(
            return_value={"_id": "saved-session-123"}
        )

        response = analyze(http)

    assert response.status_code == 200, response.text
    assert response.json()["session_id"] == "saved-session-123"

    repository.create.assert_awaited_once()

    saved = repository.create.await_args.kwargs

    assert saved["user_id"] == "test-user"
    assert saved["surah_number"] == 1
    assert saved["ayah_number"] == 1
    assert saved["expected_text"] == EXPECTED
    assert saved["recognized_text"] == EXPECTED
    assert saved["alignment"]["matched_word_count"] == len(EXPECTED.split())


def test_failed_asr_does_not_save_session(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        side_effect=ASRError("ASR unavailable"),
    ), patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:

        response = analyze(http)

    assert response.status_code == 503
    repository_class.assert_not_called()


def test_multi_ayah_analysis_saves_range(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=ASRMetadata(text=EXPECTED, tokens=[], timestamps=[], timing_type="asr_character_token_timestamps"),
    ), patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.create = AsyncMock(
            return_value={"_id": "multi-ayah-session"}
        )

        response = http.post(
            "/api/v1/recitation/analyze",
            data={
                "expected_text": get_quran_text(2, 1, 5),
                "surah_number": 2,
                "ayah_number": 1,
                "end_ayah_number": 5,
            },
            files={"audio": ("recitation.webm", WEBM, "audio/webm")},
            headers={"X-CSRF-Token": "test-csrf"},
        )

    assert response.status_code == 200, response.text
    saved = repository.create.await_args.kwargs
    assert saved["surah_number"] == 2
    assert saved["ayah_number"] == 1
    assert saved["end_ayah_number"] == 5


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (5, 2),
        (1, 11),
    ],
)
def test_invalid_ayah_range_rejected(client, start, end):
    http, _ = client

    response = http.post(
        "/api/v1/recitation/analyze",
        data={
            "expected_text": EXPECTED,
            "surah_number": 2,
            "ayah_number": start,
            "end_ayah_number": end,
        },
        files={"audio": ("recitation.webm", WEBM, "audio/webm")},
        headers={"X-CSRF-Token": "test-csrf"},
    )

    assert response.status_code == 422


def test_single_ayah_defaults_end_to_start(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=ASRMetadata(text=EXPECTED, tokens=[], timestamps=[], timing_type="asr_character_token_timestamps"),
    ), patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.create = AsyncMock(
            return_value={"_id": "single-ayah-session"}
        )

        response = analyze(http)

    assert response.status_code == 200, response.text
    saved = repository.create.await_args.kwargs
    assert saved["ayah_number"] == 1
    assert saved["end_ayah_number"] == 1


def test_tampered_expected_text_rejected_before_asr(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
    ) as mock_asr, patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:
        response = analyze(
            http,
            expected_text="نص مختلف عن الآية الصحيحة",
        )

    assert response.status_code == 422
    assert "does not match" in response.json()["detail"]
    mock_asr.assert_not_awaited()
    repository_class.assert_not_called()


def test_ayah_outside_surah_rejected_before_asr(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
    ) as mock_asr, patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:
        response = http.post(
            "/api/v1/recitation/analyze",
            data={
                "expected_text": EXPECTED,
                "surah_number": 1,
                "ayah_number": 8,
            },
            files={"audio": ("recitation.webm", WEBM, "audio/webm")},
            headers={"X-CSRF-Token": "test-csrf"},
        )

    assert response.status_code == 422
    mock_asr.assert_not_awaited()
    repository_class.assert_not_called()


def test_multi_ayah_text_mismatch_rejected(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
    ) as mock_asr, patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:
        response = http.post(
            "/api/v1/recitation/analyze",
            data={
                "expected_text": get_quran_text(2, 1, 3),
                "surah_number": 2,
                "ayah_number": 1,
                "end_ayah_number": 5,
            },
            files={"audio": ("recitation.webm", WEBM, "audio/webm")},
            headers={"X-CSRF-Token": "test-csrf"},
        )

    assert response.status_code == 422
    mock_asr.assert_not_awaited()
    repository_class.assert_not_called()


@pytest.mark.parametrize(
    "dataset_error",
    [
        "Quran dataset unavailable",
        "Invalid Quran dataset structure",
    ],
)
def test_quran_dataset_failure_returns_503_before_asr(client, dataset_error):
    from app.services.quran_text import QuranDatasetError

    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.get_quran_text",
        side_effect=QuranDatasetError(dataset_error),
    ), patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
    ) as mock_asr, patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:

        response = analyze(http)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Quran text is temporarily unavailable"
    )

    assert dataset_error not in response.text
    mock_asr.assert_not_awaited()
    repository_class.assert_not_called()


def test_whitespace_variations_accepted(client):
    http, _ = client

    submitted_text = "   \n  ".join(EXPECTED.split())

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
        return_value=ASRMetadata(text=EXPECTED, tokens=[], timestamps=[], timing_type="asr_character_token_timestamps"),
    ), patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.create = AsyncMock(
            return_value={"_id": "whitespace-session"}
        )

        response = analyze(http, expected_text=submitted_text)

    assert response.status_code == 200, response.text

    saved = repository.create.await_args.kwargs
    assert saved["expected_text"] == EXPECTED


def test_removed_diacritics_rejected_before_asr(client):
    import unicodedata

    http, _ = client

    without_diacritics = "".join(
        char
        for char in EXPECTED
        if not unicodedata.category(char).startswith("M")
    )

    assert without_diacritics != EXPECTED

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
        new_callable=AsyncMock,
    ) as mock_asr, patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:
        response = analyze(
            http,
            expected_text=without_diacritics,
        )

    assert response.status_code == 422
    mock_asr.assert_not_awaited()
    repository_class.assert_not_called()
