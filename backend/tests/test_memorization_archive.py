import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.repositories.memorization import MemorizationRepository
from bson import ObjectId


def test_archived_plan_rejects_new_session():
    db = MagicMock()
    plan_id = ObjectId()

    db["memorization_plans"].find_one = AsyncMock(
        return_value={
            "_id": plan_id,
            "user_id": "student-1",
            "status": "archived",
        }
    )
    db["memorization_sessions"].insert_one = AsyncMock()

    repository = MemorizationRepository(db)

    async def check():
        with pytest.raises(ValueError, match="archived plans"):
            await repository.create_session(
                user_id="student-1",
                plan_id=str(plan_id),
                session_type="revision",
                result="completed",
            )

    asyncio.run(check())
    db["memorization_sessions"].insert_one.assert_not_awaited()


def test_archived_plans_excluded_from_progress_query():
    db = MagicMock()
    cursor = db["memorization_plans"].find.return_value
    cursor.to_list = AsyncMock(return_value=[])

    repository = MemorizationRepository(db)

    asyncio.run(
        repository.list_all_plans_for_progress(user_id="student-1")
    )

    db["memorization_plans"].find.assert_called_once_with(
        {"user_id": "student-1", "status": {"$ne": "archived"}},
        projection={
            "surah_number": 1,
            "start_ayah": 1,
            "end_ayah": 1,
            "status": 1,
        },
    )


def test_archived_plan_api_returns_409():
    from app.api.v1.memorization import get_auth_service
    from app.main import app
    from fastapi.testclient import TestClient

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "student-1"}
    )
    auth.verify_csrf = AsyncMock(return_value=True)

    db = MagicMock()
    from tests.memorization_transaction_mocks import configure_transaction
    configure_transaction(db)
    plan_id = ObjectId()
    db["memorization_plans"].find_one_and_update = AsyncMock(return_value=None)
    db["memorization_plans"].find_one = AsyncMock(
        return_value={
            "_id": plan_id,
            "user_id": "student-1",
            "status": "archived",
        }
    )
    db["memorization_sessions"].insert_one = AsyncMock()

    original_database = getattr(app.state, "database", None)
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            app.state.database = db
            client.cookies.set("quran_session", "test-session")
            response = client.post(
                f"/api/v1/memorization/plans/{plan_id}/sessions",
                headers={"X-CSRF-Token": "valid-token"},
                json={
                    "session_type": "revision",
                    "result": "completed",
                },
            )

        assert response.status_code == 409, response.text
        assert response.json()["detail"] == "Memorization plan is archived"
        db["memorization_sessions"].insert_one.assert_not_awaited()
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.state.database = original_database


def test_archived_plan_cannot_be_reactivated():
    db = MagicMock()
    plan_id = ObjectId()
    plans = db["memorization_plans"]
    plans.find_one_and_update = AsyncMock(return_value=None)

    repository = MemorizationRepository(db)

    result = asyncio.run(
        repository.update_plan(
            user_id="student-1",
            plan_id=str(plan_id),
            status="active",
        )
    )

    assert result is None
    plans.find_one_and_update.assert_awaited_once()

    query = plans.find_one_and_update.await_args.args[0]
    assert query == {
        "_id": plan_id,
        "user_id": "student-1",
        "status": {"$ne": "archived"},
    }
