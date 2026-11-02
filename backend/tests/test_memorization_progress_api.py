"""API tests for memorization progress."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.memorization import get_current_memorization_user
from app.main import app
from fastapi.testclient import TestClient

URL = "/api/v1/memorization/progress"

EMPTY_PROGRESS = {
    "total_plans": 0,
    "completed_plans": 0,
    "unique_planned_ayahs": 0,
    "completed_ayahs": 0,
    "completion_rate": 0.0,
    "revision_sessions": 0,
}


def test_progress_requires_authentication():
    from fastapi import HTTPException

    async def reject_user():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_memorization_user] = reject_user
    try:
        with TestClient(app) as client:
            response = client.get(URL)
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_current_memorization_user, None)


def test_progress_empty():
    async def authenticated_user():
        return {"_id": "user-1"}

    app.dependency_overrides[get_current_memorization_user] = authenticated_user
    try:
        with patch(
            "app.services.memorization.MemorizationService.get_progress",
            new_callable=AsyncMock,
            return_value=EMPTY_PROGRESS,
        ):
            with TestClient(app) as client:
                with patch.object(client.app.state, "database", MagicMock()):
                    response = client.get(URL)

        assert response.status_code == 200
        assert response.json() == EMPTY_PROGRESS
    finally:
        app.dependency_overrides.pop(get_current_memorization_user, None)


def test_progress_with_data():
    async def authenticated_user():
        return {"_id": "user-1"}

    progress = {
        "total_plans": 2,
        "completed_plans": 1,
        "unique_planned_ayahs": 15,
        "completed_ayahs": 10,
        "completion_rate": 66.67,
        "revision_sessions": 3,
    }

    app.dependency_overrides[get_current_memorization_user] = authenticated_user
    try:
        with patch(
            "app.services.memorization.MemorizationService.get_progress",
            new_callable=AsyncMock,
            return_value=progress,
        ):
            with TestClient(app) as client:
                with patch.object(client.app.state, "database", MagicMock()):
                    response = client.get(URL)

        assert response.status_code == 200
        assert response.json() == progress
    finally:
        app.dependency_overrides.pop(get_current_memorization_user, None)
