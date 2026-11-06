from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.v1.auth import get_auth_service
from app.main import app
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError


@pytest.mark.parametrize(
    ("recitation", "expected_status"),
    [
        ("valid", 201),
        ("missing", 404),
        ("wrong_user", 404),
        ("wrong_surah", 422),
        ("outside_range", 422),
        ("duplicate", 409),
        ("unrelated_duplicate", 500),
        ("invalid_id", 422),
        ("missing_plan", 404),
    ],
)
def test_recitation_memorization_link_http(recitation, expected_status):
    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value={"_id": "user-1"})
    auth.verify_csrf = AsyncMock(return_value=True)

    plan_id = ObjectId()
    recitation_id = ObjectId()
    session_id = ObjectId()

    database = MagicMock()
    from tests.memorization_transaction_mocks import configure_transaction
    configure_transaction(database)
    plans = MagicMock()
    recitations = MagicMock()
    sessions = MagicMock()

    database.__getitem__.side_effect = {
        "memorization_plans": plans,
        "recitation_sessions": recitations,
        "memorization_sessions": sessions,
    }.__getitem__

    plans.find_one = AsyncMock(
        return_value={
            "_id": plan_id,
            "user_id": "user-1",
            "surah_number": 1,
            "start_ayah": 2,
            "end_ayah": 5,
        }
    )

    plans.find_one_and_update = AsyncMock(
        return_value=plans.find_one.return_value
    )

    if recitation == "missing_plan":
        plans.find_one = AsyncMock(return_value=None)

    recitation_document = {
        "_id": recitation_id,
        "user_id": "user-1",
        "surah_number": 1,
        "ayah_number": 2,
        "end_ayah_number": 4,
    }

    if recitation == "missing":
        recitations.find_one = AsyncMock(return_value=None)
    elif recitation == "wrong_user":
        recitations.find_one = AsyncMock(return_value=None)
    else:
        if recitation == "wrong_surah":
            recitation_document["surah_number"] = 2
        if recitation == "outside_range":
            recitation_document["end_ayah_number"] = 6
        recitations.find_one = AsyncMock(return_value=recitation_document)

    if recitation == "unrelated_duplicate":
        sessions.insert_one = AsyncMock(
            side_effect=DuplicateKeyError(
                "E11000 duplicate key index: unrelated_unique_index"
            )
        )
    elif recitation == "duplicate":
        sessions.insert_one = AsyncMock(
            side_effect=DuplicateKeyError(
                "E11000 duplicate key index: unique_recitation_session_link"
            )
        )
    else:
        sessions.insert_one = AsyncMock(
            return_value=SimpleNamespace(inserted_id=session_id)
        )

    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            app.state.database = database
            client.cookies.set("quran_session", "test-session")

            response = client.post(
                f"/api/v1/memorization/plans/{plan_id}/sessions",
                headers={"X-CSRF-Token": "valid-token"},
                json={
                    "session_type": "memorization",
                    "result": "needs_review",
                    "recitation_session_id": (
                        "invalid-id"
                        if recitation == "invalid_id"
                        else str(recitation_id)
                    ),
                },
            )

        assert response.status_code == expected_status, response.text

        if recitation in ("invalid_id", "missing_plan"):
            recitations.find_one.assert_not_awaited()
        else:
            recitations.find_one.assert_awaited_once_with(
                {
                    "_id": recitation_id,
                    "user_id": "user-1",
                }
            )

        if expected_status == 201:
            assert response.json()["recitation_session_id"] == str(recitation_id)
            document = sessions.insert_one.await_args.args[0]
            assert document["recitation_session_id"] == recitation_id

        if expected_status in (404, 422):
            sessions.insert_one.assert_not_awaited()

        if expected_status == 409:
            assert response.json()["detail"] == "Recitation session already linked"

    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)
