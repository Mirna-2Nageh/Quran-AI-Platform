"""HTTP integration tests for chunk-based memorization correction."""

from unittest.mock import AsyncMock, patch

import pytest
from app.api.v1.auth import get_auth_service
from app.main import app
from app.services.live_audio import MAX_CHUNK_BYTES
from app.services.quran_asr import ASRError
from fastapi.testclient import TestClient

WEBM = b"\x1a\x45\xdf\xa3" + b"test-audio-data"
URL = "/api/v1/recitation/live-correction"


@pytest.fixture
def client():
    service = AsyncMock()
    service.get_current_user.return_value = {"_id": "test-user"}
    service.verify_csrf.return_value = True

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as http:
            http.cookies.set("quran_session", "test-session")
            yield http, service
    finally:
        app.dependency_overrides.clear()


def submit(
    http,
    content=WEBM,
    content_type="audio/webm",
    start_word_index=0,
    headers=None,
    surah_number=1,
    ayah_number=1,
):
    return http.post(
        URL,
        data={
            "surah_number": surah_number,
            "ayah_number": ayah_number,
            "start_word_index": start_word_index,
        },
        files={"audio": ("chunk.webm", content, content_type)},
        headers={
            "X-CSRF-Token": "test-csrf",
            **(headers or {}),
        },
    )


def test_successful_live_correction(client):
    http, _ = client

    with patch(
        "app.api.v1.live_correction.transcribe_live_chunk",
        new_callable=AsyncMock,
        return_value={"text": "بسم الله"},
    ) as mock_asr:
        response = submit(http)

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["recognized_text"] == "بسم الله"
    assert data["analysis_type"] == "chunk_based_word_alignment"
    assert data["next_word_index"] == 2
    assert data["has_more_words"] is True
    assert data["word_feedback"][0]["status"] == "matched"
    assert data["word_feedback"][1]["status"] == "matched"
    assert data["alignment"]["matched_word_count"] == 2
    mock_asr.assert_awaited_once()


def test_unauthenticated_user(client):
    http, service = client
    service.get_current_user.return_value = None

    response = submit(http)

    assert response.status_code == 401


def test_invalid_csrf(client):
    http, service = client
    service.verify_csrf.return_value = False

    response = submit(http)

    assert response.status_code == 403


def test_unsupported_audio_format(client):
    http, _ = client

    response = submit(http, content_type="audio/wav")

    assert response.status_code == 415


def test_invalid_audio_signature(client):
    http, _ = client

    response = submit(http, content=b"not-real-webm")

    assert response.status_code == 415


def test_oversized_audio(client):
    http, _ = client

    response = submit(
        http,
        content=b"\x1a\x45\xdf\xa3" + b"x" * MAX_CHUNK_BYTES,
    )

    assert response.status_code == 413


def test_invalid_start_word_index(client):
    http, _ = client

    response = submit(http, start_word_index=999)

    assert response.status_code == 422


def test_invalid_ayah_number(client):
    http, _ = client

    response = submit(http, ayah_number=999)

    assert response.status_code == 422


def test_asr_failure(client):
    http, _ = client

    with patch(
        "app.api.v1.live_correction.transcribe_live_chunk",
        new_callable=AsyncMock,
        side_effect=ASRError("Worker unavailable"),
    ):
        response = submit(http)

    assert response.status_code == 503


def test_missing_asr_manager(client):
    http, _ = client

    original = http.app.state.asr_manager
    http.app.state.asr_manager = None

    try:
        response = submit(http)
    finally:
        http.app.state.asr_manager = original

    assert response.status_code == 503


def test_pending_words_not_reported_as_errors(client):
    http, _ = client

    with patch(
        "app.api.v1.live_correction.transcribe_live_chunk",
        new_callable=AsyncMock,
        return_value={"text": "بسم الله"},
    ):
        response = submit(http)

    assert response.status_code == 200, response.text

    data = response.json()
    pending = [
        item for item in data["word_feedback"]
        if item["status"] == "pending"
    ]

    assert pending
    assert all(item["recognized_word"] is None for item in pending)
    assert data["alignment"]["issues"] == []
