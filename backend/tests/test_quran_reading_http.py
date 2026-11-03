"""HTTP integration tests for Quran reading."""

from unittest.mock import AsyncMock, MagicMock

from app.api.v1 import quran_reading
from app.api.v1.auth import get_auth_service
from app.main import app
from fastapi.testclient import TestClient

from tests.quran_reading_fakes import FakeQuranReadingRepository


def test_bookmark_crud(monkeypatch):
    FakeQuranReadingRepository.reset()
    monkeypatch.setattr(
        quran_reading,
        "QuranReadingRepository",
        FakeQuranReadingRepository,
    )

    service = MagicMock()
    service.get_current_user = AsyncMock(
        return_value={"_id": "user-a"}
    )
    service.verify_csrf = AsyncMock(return_value=True)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "session-a")
            headers = {"X-CSRF-Token": "valid"}

            url = "/api/v1/quran/bookmarks/1/1"
            first = client.put(url, headers=headers)
            second = client.put(url, headers=headers)
            listing = client.get("/api/v1/quran/bookmarks")
            deleted = client.delete(url, headers=headers)
            after = client.get("/api/v1/quran/bookmarks")

        assert first.status_code == 200
        assert second.status_code == 200
        assert listing.status_code == 200
        assert listing.json()["count"] == 1
        assert deleted.json()["deleted"] is True
        assert after.json()["count"] == 0
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_bookmarks_are_isolated_between_users(monkeypatch):
    FakeQuranReadingRepository.reset()
    monkeypatch.setattr(
        quran_reading, "QuranReadingRepository",
        FakeQuranReadingRepository,
    )

    current = {"id": "user-a"}
    service = MagicMock()
    service.get_current_user = AsyncMock(
        side_effect=lambda token: {"_id": current["id"]}
    )
    service.verify_csrf = AsyncMock(return_value=True)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "session")
            headers = {"X-CSRF-Token": "valid"}
            url = "/api/v1/quran/bookmarks/1/1"

            assert client.put(url, headers=headers).status_code == 200
            current["id"] = "user-b"

            listing = client.get("/api/v1/quran/bookmarks")
            deletion = client.delete(url, headers=headers)

            assert listing.json()["count"] == 0
            assert deletion.json()["deleted"] is False

            current["id"] = "user-a"
            assert client.get(
                "/api/v1/quran/bookmarks"
            ).json()["count"] == 1
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_reading_progress_is_user_scoped(monkeypatch):
    FakeQuranReadingRepository.reset()
    monkeypatch.setattr(
        quran_reading, "QuranReadingRepository",
        FakeQuranReadingRepository,
    )

    current = {"id": "user-a"}
    service = MagicMock()
    service.get_current_user = AsyncMock(
        side_effect=lambda token: {"_id": current["id"]}
    )
    service.verify_csrf = AsyncMock(return_value=True)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "session")
            url = "/api/v1/quran/progress"

            assert client.get(url).json() is None

            saved = client.put(
                url,
                headers={"X-CSRF-Token": "valid"},
                json={"surah_number": 2, "ayah_number": 5},
            )
            assert saved.status_code == 200

            current["id"] = "user-b"
            assert client.get(url).json() is None

            current["id"] = "user-a"
            progress = client.get(url)
            assert progress.status_code == 200
            assert progress.json()["surah_number"] == 2
            assert progress.json()["ayah_number"] == 5
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
