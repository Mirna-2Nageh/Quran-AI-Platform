"""Authentication coverage for live session lifecycle."""

from unittest.mock import AsyncMock, MagicMock

from app.api.v1.auth import get_auth_service
from app.main import app
from fastapi.testclient import TestClient


def test_live_session_requires_auth():
    service = MagicMock()
    service.get_current_user = AsyncMock(return_value=None)

    old_override = app.dependency_overrides.get(get_auth_service)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            start = client.post(
                "/api/v1/recitation/live-sessions/start",
                json={"surah_number": 1, "ayah_number": 1},
            )
            finalize = client.post("/api/v1/recitation/live-sessions/example/finalize")

        assert start.status_code == 401
        assert finalize.status_code == 401
    finally:
        if old_override is None:
            app.dependency_overrides.pop(get_auth_service, None)
        else:
            app.dependency_overrides[get_auth_service] = old_override


def test_live_session_start_authenticated(monkeypatch):
    from app.api.v1 import live_sessions

    service = MagicMock()
    service.get_current_user = AsyncMock(return_value={"_id": "user-1"})
    service.verify_csrf = AsyncMock(return_value=True)

    repo = MagicMock()
    repo.create = AsyncMock(return_value={"session_id": "live-123", "status": "active"})

    monkeypatch.setattr(
        live_sessions, "LiveRecitationSessionRepository", lambda db: repo
    )
    monkeypatch.setattr(live_sessions, "get_quran_text", lambda *args: "بسم الله")

    old = app.dependency_overrides.get(get_auth_service)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/recitation/live-sessions/start",
                json={"surah_number": 1, "ayah_number": 1},
            )
        assert response.status_code == 200
        assert response.json()["session_id"] == "live-123"
        assert repo.create.await_args.kwargs["user_id"] == "user-1"
    finally:
        if old is None:
            app.dependency_overrides.pop(get_auth_service, None)
        else:
            app.dependency_overrides[get_auth_service] = old


def test_live_session_finalize_authenticated(monkeypatch):
    from app.api.v1 import live_sessions

    service = MagicMock()
    service.get_current_user = AsyncMock(return_value={"_id": "user-1"})
    service.verify_csrf = AsyncMock(return_value=True)

    repo = MagicMock()
    repo.finalize_atomic = AsyncMock(return_value="history-123")

    monkeypatch.setattr(
        live_sessions, "LiveRecitationSessionRepository", lambda db: repo
    )

    old = app.dependency_overrides.get(get_auth_service)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/recitation/live-sessions/live-123/finalize")

        assert response.status_code == 200
        assert response.json() == {
            "session_id": "live-123",
            "recitation_session_id": "history-123",
            "status": "finalized",
        }
        assert repo.finalize_atomic.await_args.kwargs["user_id"] == "user-1"
    finally:
        if old is None:
            app.dependency_overrides.pop(get_auth_service, None)
        else:
            app.dependency_overrides[get_auth_service] = old
