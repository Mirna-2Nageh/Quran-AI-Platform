"""Memorization API security tests."""

from app.api.v1.auth import get_auth_service
from app.main import app
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_create_plan_without_database():
    def unavailable_database():
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    app.dependency_overrides[get_auth_service] = unavailable_database

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/memorization/plans",
                json={
                    "surah_number": 1,
                    "start_ayah": 1,
                    "end_ayah": 7,
                },
            )

        assert response.status_code == 503
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_create_plan_requires_authentication():
    from unittest.mock import AsyncMock, MagicMock

    service = MagicMock()
    service.get_current_user = AsyncMock(return_value=None)

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/memorization/plans",
                json={
                    "surah_number": 1,
                    "start_ayah": 1,
                    "end_ayah": 7,
                },
            )

        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
        service.verify_csrf.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_create_plan_rejects_invalid_csrf():
    from unittest.mock import AsyncMock, MagicMock

    service = MagicMock()
    service.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    service.verify_csrf = AsyncMock(return_value=False)

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "test-session")
            response = client.post(
                "/api/v1/memorization/plans",
                headers={"X-CSRF-Token": "invalid-token"},
                json={
                    "surah_number": 1,
                    "start_ayah": 1,
                    "end_ayah": 7,
                },
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid CSRF token"
        service.verify_csrf.assert_awaited_once_with(
            "test-session", "invalid-token"
        )
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_create_plan_rejects_invalid_quran_range():
    from unittest.mock import AsyncMock, MagicMock

    service = MagicMock()
    service.database = MagicMock()
    service.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    service.verify_csrf = AsyncMock(return_value=True)

    app.dependency_overrides[get_auth_service] = lambda: service
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = service.database
            client.cookies.set("quran_session", "test-session")

            response = client.post(
                "/api/v1/memorization/plans",
                headers={"X-CSRF-Token": "valid-token"},
                json={
                    "surah_number": 1,
                    "start_ayah": 1,
                    "end_ayah": 100,
                },
            )

        assert response.status_code == 422
        service.verify_csrf.assert_awaited_once()
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)


def test_create_plan_success():
    from unittest.mock import AsyncMock, MagicMock

    from bson import ObjectId

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    auth.verify_csrf = AsyncMock(return_value=True)

    database = MagicMock()
    inserted_id = ObjectId()
    database["memorization_plans"].insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=inserted_id)
    )

    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = database
            client.cookies.set("quran_session", "test-session")
            response = client.post(
                "/api/v1/memorization/plans",
                headers={"X-CSRF-Token": "valid-token"},
                json={
                    "surah_number": 1,
                    "start_ayah": 1,
                    "end_ayah": 7,
                },
            )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["id"] == str(inserted_id)
        assert data["status"] == "active"
        assert data["surah_number"] == 1
        assert data["start_ayah"] == 1
        assert data["end_ayah"] == 7
        assert data["created_at"]
        assert data["updated_at"]

        database["memorization_plans"].insert_one.assert_awaited_once()
        document = (
            database["memorization_plans"].insert_one.await_args.args[0]
        )
        assert document["user_id"] == "test-user"
        auth.verify_csrf.assert_awaited_once_with(
            "test-session", "valid-token"
        )
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)


def test_list_plans_requires_authentication():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/memorization/plans")

        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_list_plans_rejects_invalid_limit():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            for limit in (0, -1, 51):
                response = client.get(
                    "/api/v1/memorization/plans",
                    params={"limit": limit},
                )
                assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_list_plans_returns_empty_list():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )

    database = MagicMock()
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[])
    database["memorization_plans"].find.return_value = cursor

    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = database
            response = client.get("/api/v1/memorization/plans")

        assert response.status_code == 200, response.text
        assert response.json() == []
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)


def test_list_plans_success():
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, MagicMock

    from bson import ObjectId

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )

    now = datetime.now(timezone.utc)
    plan_id = ObjectId()
    database = MagicMock()
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[{
        "_id": plan_id,
        "user_id": "test-user",
        "surah_number": 1,
        "start_ayah": 1,
        "end_ayah": 7,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }])
    collection = database["memorization_plans"]
    collection.find.return_value = cursor

    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = database
            response = client.get(
                "/api/v1/memorization/plans",
                params={"limit": 10},
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(plan_id)
        assert data[0]["status"] == "active"
        assert data[0]["surah_number"] == 1
        assert data[0]["start_ayah"] == 1
        assert data[0]["end_ayah"] == 7

        collection.find.assert_called_once_with(
            {"user_id": "test-user"}
        )
        cursor.sort.assert_called_once_with(
            [("created_at", -1), ("_id", -1)]
        )
        cursor.limit.assert_called_once_with(10)
        cursor.to_list.assert_awaited_once_with(length=10)
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)


def test_get_plan_requires_authentication():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/memorization/plans/507f1f77bcf86cd799439011"
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_get_plan_invalid_id_returns_404():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = MagicMock()
            response = client.get(
                "/api/v1/memorization/plans/invalid-id"
            )
        assert response.status_code == 404
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)


def test_get_plan_not_found_returns_404():
    from unittest.mock import AsyncMock, MagicMock

    from bson import ObjectId

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    database = MagicMock()
    collection = database["memorization_plans"]
    collection.find_one = AsyncMock(return_value=None)
    plan_id = str(ObjectId())

    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = database
            response = client.get(
                f"/api/v1/memorization/plans/{plan_id}"
            )

        assert response.status_code == 404
        collection.find_one.assert_awaited_once_with({
            "_id": ObjectId(plan_id),
            "user_id": "test-user",
        })
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)


def test_get_plan_success():
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, MagicMock

    from bson import ObjectId

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )

    plan_id = ObjectId()
    now = datetime.now(timezone.utc)
    database = MagicMock()
    collection = database["memorization_plans"]
    collection.find_one = AsyncMock(return_value={
        "_id": plan_id,
        "user_id": "test-user",
        "surah_number": 1,
        "start_ayah": 1,
        "end_ayah": 7,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })

    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = database
            response = client.get(
                f"/api/v1/memorization/plans/{plan_id}"
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == str(plan_id)
        assert data["surah_number"] == 1
        assert data["start_ayah"] == 1
        assert data["end_ayah"] == 7
        assert data["status"] == "active"
        assert data["created_at"]
        assert data["updated_at"]

        collection.find_one.assert_awaited_once_with({
            "_id": plan_id,
            "user_id": "test-user",
        })
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)


def test_update_plan_requires_authentication():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/memorization/plans/507f1f77bcf86cd799439011",
                json={"status": "completed"},
            )

        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_update_plan_rejects_invalid_csrf():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    auth.verify_csrf = AsyncMock(return_value=False)
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "test-session")
            response = client.patch(
                "/api/v1/memorization/plans/507f1f77bcf86cd799439011",
                headers={"X-CSRF-Token": "invalid-token"},
                json={"status": "completed"},
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid CSRF token"
        auth.verify_csrf.assert_awaited_once_with(
            "test-session", "invalid-token"
        )
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_update_plan_success():
    from datetime import datetime, timedelta, timezone
    from unittest.mock import AsyncMock, MagicMock

    from bson import ObjectId

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    auth.verify_csrf = AsyncMock(return_value=True)

    plan_id = ObjectId()
    created_at = datetime.now(timezone.utc) - timedelta(days=1)
    updated_at = datetime.now(timezone.utc)

    database = MagicMock()
    from tests.memorization_transaction_mocks import configure_transaction
    configure_transaction(database)
    collection = database["memorization_plans"]
    collection.find_one = AsyncMock(return_value={
        "_id": plan_id,
        "user_id": "test-user",
        "status": "active",
    })
    collection.find_one_and_update = AsyncMock(return_value={
        "_id": plan_id,
        "user_id": "test-user",
        "surah_number": 1,
        "start_ayah": 1,
        "end_ayah": 7,
        "status": "completed",
        "created_at": created_at,
        "updated_at": updated_at,
    })

    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = database
            client.cookies.set("quran_session", "test-session")
            response = client.patch(
                f"/api/v1/memorization/plans/{plan_id}",
                headers={"X-CSRF-Token": "valid-token"},
                json={"status": "completed"},
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == str(plan_id)
        assert data["status"] == "completed"

        collection.find_one_and_update.assert_awaited_once()
        args, kwargs = collection.find_one_and_update.await_args
        assert args[0] == {
            "_id": plan_id,
            "user_id": "test-user",
            "status": {"$ne": "archived"},
        }
        assert args[1]["$set"]["status"] == "completed"
        assert "updated_at" in args[1]["$set"]
        assert "created_at" not in args[1]["$set"]
        assert kwargs["return_document"] is True
        auth.verify_csrf.assert_awaited_once_with(
            "test-session", "valid-token"
        )
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)


def test_update_plan_invalid_id_returns_404():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value={"_id": "test-user"})
    auth.verify_csrf = AsyncMock(return_value=True)

    app.dependency_overrides[get_auth_service] = lambda: auth
    original = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = MagicMock()
            client.cookies.set("quran_session", "test-session")
            response = client.patch(
                "/api/v1/memorization/plans/invalid-id",
                headers={"X-CSRF-Token": "valid-token"},
                json={"status": "completed"},
            )
        assert response.status_code == 404
    finally:
        app.state.database = original
        app.dependency_overrides.pop(get_auth_service, None)


def test_update_plan_not_found_returns_404():
    from unittest.mock import AsyncMock, MagicMock

    from bson import ObjectId

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value={"_id": "test-user"})
    auth.verify_csrf = AsyncMock(return_value=True)

    database = MagicMock()
    from tests.memorization_transaction_mocks import configure_transaction
    configure_transaction(database)
    collection = database["memorization_plans"]
    collection.find_one = AsyncMock(return_value=None)
    collection.find_one_and_update = AsyncMock(return_value=None)
    plan_id = ObjectId()

    app.dependency_overrides[get_auth_service] = lambda: auth
    original = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = database
            client.cookies.set("quran_session", "test-session")
            response = client.patch(
                f"/api/v1/memorization/plans/{plan_id}",
                headers={"X-CSRF-Token": "valid-token"},
                json={"status": "completed"},
            )

        assert response.status_code == 404
        collection.find_one.assert_awaited_once()
        collection.find_one_and_update.assert_not_awaited()

    finally:
        app.state.database = original
        app.dependency_overrides.pop(get_auth_service, None)


def test_update_plan_rejects_invalid_status():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value={"_id": "test-user"})
    auth.verify_csrf = AsyncMock(return_value=True)

    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "test-session")
            response = client.patch(
                "/api/v1/memorization/plans/507f1f77bcf86cd799439011",
                headers={"X-CSRF-Token": "valid-token"},
                json={"status": "invalid-status"},
            )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_create_session_requires_authentication():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)
    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/memorization/plans/507f1f77bcf86cd799439011/sessions",
                json={
                    "session_type": "memorization",
                    "result": "completed",
                },
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_create_session_rejects_invalid_csrf():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    auth.verify_csrf = AsyncMock(return_value=False)

    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            client.cookies.set("quran_session", "test-session")
            response = client.post(
                "/api/v1/memorization/plans/507f1f77bcf86cd799439011/sessions",
                headers={"X-CSRF-Token": "invalid-token"},
                json={
                    "session_type": "memorization",
                    "result": "completed",
                },
            )

        assert response.status_code == 403
        auth.verify_csrf.assert_awaited_once_with(
            "test-session", "invalid-token"
        )
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_list_sessions_requires_authentication():
    from unittest.mock import AsyncMock, MagicMock

    auth = MagicMock()
    auth.get_current_user = AsyncMock(return_value=None)

    app.dependency_overrides[get_auth_service] = lambda: auth

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/memorization/plans/507f1f77bcf86cd799439011/sessions"
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_create_session_success():
    from datetime import datetime
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from bson import ObjectId

    auth = MagicMock()
    auth.get_current_user = AsyncMock(
        return_value={"_id": "test-user"}
    )
    auth.verify_csrf = AsyncMock(return_value=True)

    plan_id = ObjectId()
    session_id = ObjectId()

    database = MagicMock()
    from tests.memorization_transaction_mocks import configure_transaction
    configure_transaction(database)
    plans = database["memorization_plans"]
    sessions = database["memorization_sessions"]

    plans.find_one_and_update = AsyncMock(
        return_value={
            "_id": plan_id,
            "user_id": "test-user",
        }
    )

    sessions.insert_one = AsyncMock(
        return_value=SimpleNamespace(inserted_id=session_id)
    )

    app.dependency_overrides[get_auth_service] = lambda: auth
    original_database = getattr(app.state, "database", None)

    try:
        with TestClient(app) as client:
            app.state.database = database
            client.cookies.set("quran_session", "test-session")

            response = client.post(
                f"/api/v1/memorization/plans/{plan_id}/sessions",
                headers={"X-CSRF-Token": "valid-token"},
                json={
                    "session_type": "memorization",
                    "result": "completed",
                    "notes": "Surah Al-Fatiha",
                },
            )

        assert response.status_code == 201, response.text

        data = response.json()
        assert data["id"] == str(session_id)
        assert data["plan_id"] == str(plan_id)
        assert data["session_type"] == "memorization"
        assert data["result"] == "completed"
        assert data["notes"] == "Surah Al-Fatiha"
        assert datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))

        plans.find_one_and_update.assert_awaited_once()
        assert plans.find_one_and_update.await_args.kwargs["session"] is not None

        sessions.insert_one.assert_awaited_once()
        document = sessions.insert_one.await_args.args[0]

        assert document["user_id"] == "test-user"
        assert document["plan_id"] == plan_id
        assert document["session_type"] == "memorization"
        assert document["result"] == "completed"
        assert document["notes"] == "Surah Al-Fatiha"

        auth.verify_csrf.assert_awaited_once_with(
            "test-session",
            "valid-token",
        )
    finally:
        app.state.database = original_database
        app.dependency_overrides.pop(get_auth_service, None)
