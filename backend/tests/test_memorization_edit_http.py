"""HTTP tests for editing memorization plans."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.v1.auth import get_auth_service
from app.main import app
from bson import ObjectId
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("status", "sessions_exist", "payload", "expected"),
    [
        ("active", False, {"end_ayah": 5}, 200),
        ("active", True, {"end_ayah": 5}, 409),
        ("active", False, {"end_ayah": 100}, 422),
        ("archived", False, {"end_ayah": 5}, 409),
    ],
)
def test_edit_plan_http(status, sessions_exist, payload, expected):
    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    auth.verify_csrf = AsyncMock(return_value=True)

    plan_id = ObjectId()
    now = datetime.now(timezone.utc)
    plan = {
        "_id": plan_id,
        "user_id": "test-user",
        "surah_number": 1,
        "start_ayah": 1,
        "end_ayah": 7,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }

    database = MagicMock()
    plans = database["memorization_plans"]
    sessions = database["memorization_sessions"]

    plans.find_one = AsyncMock(return_value=plan)
    plans.find_one_and_update = AsyncMock(
        return_value={**plan, **payload}
    )
    sessions.count_documents = AsyncMock(
        return_value=int(sessions_exist)
    )

    original_database = getattr(app.state, "database", None)
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            app.state.database = database
            client.cookies.set("quran_session", "test-session")
            response = client.patch(
                f"/api/v1/memorization/plans/{plan_id}",
                headers={"X-CSRF-Token": "valid-token"},
                json=payload,
            )

        assert response.status_code == expected, response.text

        if expected == 200:
            assert response.json()["end_ayah"] == 5
            plans.find_one_and_update.assert_awaited_once()
        else:
            plans.find_one_and_update.assert_not_awaited()
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)
