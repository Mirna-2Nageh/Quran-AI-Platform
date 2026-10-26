from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import get_auth_service
from app.api.v1.audio import MAX_AUDIO_SIZE
from app.main import app


@pytest.fixture
def client():
    service = AsyncMock()
    service.get_current_user.return_value = {"_id": "test-user"}
    service.verify_csrf.return_value = True

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app, raise_server_exceptions=True) as test_client:
            yield test_client, service
    finally:
        app.dependency_overrides.clear()


def upload(client, content, content_type="audio/webm", headers=None):
    return client.post(
        "/api/v1/recitation/audio",
        files={
            "audio": ("recitation.webm", content, content_type)
        },
        cookies={"quran_session": "test-session"},
        headers={
            "X-CSRF-Token": "test-csrf",
            **(headers or {}),
        },
    )


def test_valid_webm_upload(client):
    http, _ = client

    response = upload(
        http,
        b"\x1a\x45\xdf\xa3" + b"test-audio-data",
    )

    assert response.status_code == 200
    assert response.json()["stored"] is False
    assert response.json()["analyzed"] is False


def test_empty_audio_rejected(client):
    http, _ = client

    response = upload(http, b"")

    assert response.status_code == 400


def test_unsupported_content_type_rejected(client):
    http, _ = client

    response = upload(
        http,
        b"RIFF1234",
        content_type="audio/wav",
    )

    assert response.status_code == 415


def test_invalid_audio_signature_rejected(client):
    http, _ = client

    response = upload(
        http,
        b"not-a-real-webm-file",
    )

    assert response.status_code == 415


def test_oversized_audio_rejected(client):
    http, _ = client

    response = upload(
        http,
        b"\x1a\x45\xdf\xa3" + b"x" * MAX_AUDIO_SIZE,
    )

    assert response.status_code == 413


def test_unauthenticated_user_rejected(client):
    http, service = client
    service.get_current_user.return_value = None

    response = upload(
        http,
        b"\x1a\x45\xdf\xa3test",
    )

    assert response.status_code == 401


def test_invalid_csrf_rejected(client):
    http, service = client
    service.verify_csrf.return_value = False

    response = upload(
        http,
        b"\x1a\x45\xdf\xa3test",
    )

    assert response.status_code == 403


def test_disallowed_origin_rejected(client):
    http, _ = client

    response = upload(
        http,
        b"\x1a\x45\xdf\xa3test",
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403


def test_webm_with_opus_codec_parameter(client):
    http, _ = client

    response = upload(
        http,
        b"\x1a\x45\xdf\xa3" + b"test-audio-data",
        content_type="audio/webm;codecs=opus",
    )

    assert response.status_code == 200
    assert response.json()["content_type"] == "audio/webm;codecs=opus"
