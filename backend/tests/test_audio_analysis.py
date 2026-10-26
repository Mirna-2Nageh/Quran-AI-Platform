"""Integration tests for authenticated Quran audio analysis."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import get_auth_service
from app.api.v1.audio_analysis import MAX_AUDIO_SIZE
from app.main import app
from app.services.quran_asr import ASRError


WEBM = b"\x1a\x45\xdf\xa3" + b"test-audio-data"
EXPECTED = "بسم الله الرحمن الرحيم"


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
        "app.api.v1.audio_analysis.transcribe_audio",
        new_callable=AsyncMock,
        return_value=EXPECTED,
    ) as mock_asr:
        response = analyze(http)

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["recognized_text"] == EXPECTED
    assert data["alignment"]["matched_word_count"] == 4
    assert data["alignment"]["issues"] == []
    assert data["tajweed_analyzed"] is False
    mock_asr.assert_awaited_once_with(WEBM)


def test_missing_word_detected(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio",
        new_callable=AsyncMock,
        return_value="بسم الله الرحيم",
    ):
        response = analyze(http)

    assert response.status_code == 200, response.text

    issues = response.json()["alignment"]["issues"]

    assert any(
        issue["operation"] == "deletion"
        and issue["expected_word"] == "الرحمن"
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
        "app.api.v1.audio_analysis.transcribe_audio",
        new_callable=AsyncMock,
        return_value="",
    ):
        response = analyze(http)

    assert response.status_code == 422


def test_asr_failure_returns_service_unavailable(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio",
        new_callable=AsyncMock,
        side_effect=ASRError("Model unavailable"),
    ):
        response = analyze(http)

    assert response.status_code == 503
    assert "Model unavailable" not in response.text


def test_successful_analysis_saves_session(client):
    http, service = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio",
        new_callable=AsyncMock,
        return_value=EXPECTED,
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
    assert saved["alignment"]["matched_word_count"] == 4


def test_failed_asr_does_not_save_session(client):
    http, _ = client

    with patch(
        "app.api.v1.audio_analysis.transcribe_audio",
        new_callable=AsyncMock,
        side_effect=ASRError("ASR unavailable"),
    ), patch(
        "app.api.v1.audio_analysis.RecitationSessionRepository"
    ) as repository_class:

        response = analyze(http)

    assert response.status_code == 503
    repository_class.assert_not_called()
