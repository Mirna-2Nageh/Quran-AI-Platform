"""Security tests for Quran reading API."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.v1.auth import get_auth_service
from app.main import app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/quran/bookmarks"),
        ("GET", "/api/v1/quran/progress"),
        ("PUT", "/api/v1/quran/progress"),
        ("PUT", "/api/v1/quran/bookmarks/1/1"),
        ("DELETE", "/api/v1/quran/bookmarks/1/1"),
    ],
)
def test_requires_authentication(method, path):
    service = MagicMock()
    service.get_current_user = AsyncMock(return_value=None)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.request(method, path)
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("PUT", "/api/v1/quran/bookmarks/1/1", None),
        ("DELETE", "/api/v1/quran/bookmarks/1/1", None),
        (
            "PUT",
            "/api/v1/quran/progress",
            {"surah_number": 1, "ayah_number": 1},
        ),
    ],
)
def test_write_rejects_invalid_csrf(method, path, body):
    service = MagicMock()
    service.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    service.verify_csrf = AsyncMock(return_value=False)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "test-session")
            response = client.request(
                method,
                path,
                json=body,
                headers={"X-CSRF-Token": "invalid-token"},
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid CSRF token"
        service.verify_csrf.assert_awaited_once_with(
            "test-session", "invalid-token"
        )
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


@pytest.mark.parametrize(
    "surah,ayah",
    [(115, 1), (1, 100)],
)
def test_bookmark_rejects_invalid_quran_location(surah, ayah):
    service = MagicMock()
    service.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    service.verify_csrf = AsyncMock(return_value=True)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "test-session")
            response = client.put(
                f"/api/v1/quran/bookmarks/{surah}/{ayah}",
                headers={"X-CSRF-Token": "valid-token"},
            )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
