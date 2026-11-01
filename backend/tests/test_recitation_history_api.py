"""Tests for authenticated recitation history."""

from datetime import datetime, timezone

from app.api.v1.auth import get_auth_service
from app.main import app
from bson import ObjectId
from fastapi.testclient import TestClient


class FakeAuthService:
    async def get_current_user(self, token):
        return None


def test_history_requires_authentication():
    app.dependency_overrides[get_auth_service] = (
        lambda: FakeAuthService()
    )

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/recitation/history")

        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    finally:
        app.dependency_overrides.pop(get_auth_service, None)





class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, field, direction=None):
        fields = field if isinstance(field, list) else [(field, direction)]

        for name, order in reversed(fields):
            self.documents.sort(
                key=lambda doc: doc[name],
                reverse=order == -1,
            )

        return self

    def limit(self, value):
        self.documents = self.documents[:value]
        return self

    async def to_list(self, length):
        return self.documents[:length]


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query):
        def matches(doc):
            if doc["user_id"] != query["user_id"]:
                return False

            if "$or" not in query:
                return True

            return any(
                (
                    doc["created_at"] < condition["created_at"]["$lt"]
                    if isinstance(condition["created_at"], dict)
                    else (
                        doc["created_at"] == condition["created_at"]
                        and doc["_id"] < condition["_id"]["$lt"]
                    )
                )
                for condition in query["$or"]
            )

        return FakeCursor([
            doc for doc in self.documents if matches(doc)
        ])


class AuthenticatedService:
    def __init__(self, user_id, database):
        self.user_id = user_id
        self.database = database

    async def get_current_user(self, token):
        return {
            "_id": self.user_id,
            "is_active": True,
        }


def make_session(user_id, ayah_number):
    return {
        "_id": ObjectId(),
        "user_id": user_id,
        "surah_number": 1,
        "ayah_number": ayah_number,
        "expected_text": "بسم الله الرحمن الرحيم",
        "recognized_text": "بسم الله الرحمن الرحيم",
        "alignment": {
            "issues": [],
        },
        "analysis_type": "word_level_asr_alignment",
        "tajweed_analyzed": False,
        "created_at": datetime.now(timezone.utc),
    }


def test_history_returns_only_current_user_sessions():
    current_user_id = ObjectId()
    other_user_id = ObjectId()

    documents = [
        make_session(current_user_id, 1),
        make_session(other_user_id, 2),
        make_session(current_user_id, 3),
    ]

    database = {
        "recitation_sessions": FakeCollection(documents),
    }

    service = AuthenticatedService(
        current_user_id,
        database,
    )

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/v1/recitation/history"
            )

        assert response.status_code == 200, response.text

        data = response.json()

        assert data["count"] == 2
        assert len(data["items"]) == 2

        returned_ayahs = {
            item["ayah_number"]
            for item in data["items"]
        }

        assert returned_ayahs == {1, 3}

        for item in data["items"]:
            assert item["tajweed_analyzed"] is False
            assert item["analysis_type"] == (
                "word_level_asr_alignment"
            )

    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_history_respects_limit():
    current_user_id = ObjectId()

    documents = [
        make_session(current_user_id, number)
        for number in range(1, 6)
    ]

    database = {
        "recitation_sessions": FakeCollection(documents),
    }

    service = AuthenticatedService(
        current_user_id,
        database,
    )

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/api/v1/recitation/history?limit=2"
            )

        assert response.status_code == 200, response.text
        assert response.json()["count"] == 2

    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_history_rejects_invalid_limits():
    user_id = ObjectId()
    database = {
        "recitation_sessions": FakeCollection([]),
    }
    service = AuthenticatedService(user_id, database)

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            for limit in (0, -1, 51):
                response = client.get(
                    f"/api/v1/recitation/history?limit={limit}"
                )
                assert response.status_code == 422, response.text
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_history_cursor_pagination():
    from datetime import timedelta

    user_id = ObjectId()
    other_user_id = ObjectId()

    base_time = datetime(
        2026, 11, 1, 13, 0, 0,
        tzinfo=timezone.utc,
    )

    documents = [
        make_session(user_id, number)
        for number in range(1, 6)
    ]

    for index, document in enumerate(documents):
        document["created_at"] = base_time - timedelta(
            minutes=index
        )

    other_session = make_session(other_user_id, 99)
    other_session["created_at"] = base_time
    documents.append(other_session)

    database = {
        "recitation_sessions": FakeCollection(documents),
    }

    service = AuthenticatedService(user_id, database)

    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            first = client.get(
                "/api/v1/recitation/history?limit=2"
            )
            assert first.status_code == 200, first.text

            first_data = first.json()
            assert first_data["count"] == 2
            assert first_data["has_more"] is True
            assert first_data["next_cursor"] is not None

            second = client.get(
                "/api/v1/recitation/history",
                params={
                    "limit": 2,
                    "cursor": first_data["next_cursor"],
                },
            )

            assert second.status_code == 200, second.text

            second_data = second.json()
            assert second_data["count"] == 2
            assert second_data["has_more"] is True

            third = client.get(
                "/api/v1/recitation/history",
                params={
                    "limit": 2,
                    "cursor": second_data["next_cursor"],
                },
            )

            assert third.status_code == 200, third.text

            third_data = third.json()
            assert third_data["count"] == 1
            assert third_data["has_more"] is False
            assert third_data["next_cursor"] is None

            all_items = (
                first_data["items"]
                + second_data["items"]
                + third_data["items"]
            )

            ids = [item["id"] for item in all_items]

            assert len(ids) == 5
            assert len(set(ids)) == 5
            assert all(
                item["ayah_number"] != 99
                for item in all_items
            )

    finally:
        app.dependency_overrides.pop(
            get_auth_service, None
        )


def test_history_pagination_same_timestamp():
    user_id = ObjectId()
    shared_time = datetime(
        2026, 11, 1, 13, 0, 0,
        tzinfo=timezone.utc,
    )

    documents = [
        make_session(user_id, number)
        for number in range(1, 5)
    ]

    for document in documents:
        document["created_at"] = shared_time

    database = {
        "recitation_sessions": FakeCollection(documents),
    }

    service = AuthenticatedService(user_id, database)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            first = client.get(
                "/api/v1/recitation/history?limit=2"
            )
            assert first.status_code == 200, first.text

            second = client.get(
                "/api/v1/recitation/history",
                params={
                    "limit": 2,
                    "cursor": first.json()["next_cursor"],
                },
            )
            assert second.status_code == 200, second.text

            ids = [
                item["id"]
                for item in (
                    first.json()["items"]
                    + second.json()["items"]
                )
            ]

            assert len(ids) == 4
            assert len(set(ids)) == 4
            assert second.json()["has_more"] is False

    finally:
        app.dependency_overrides.pop(
            get_auth_service, None
        )


def test_history_rejects_invalid_cursor():
    user_id = ObjectId()

    database = {
        "recitation_sessions": FakeCollection([]),
    }

    service = AuthenticatedService(user_id, database)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            for cursor in ("invalid!", "e30", "a" * 257):
                response = client.get(
                    "/api/v1/recitation/history",
                    params={"cursor": cursor},
                )

                assert response.status_code == 422

    finally:
        app.dependency_overrides.pop(
            get_auth_service, None
        )


def test_history_cursor_cannot_expose_other_user_sessions():
    user_a = ObjectId()
    user_b = ObjectId()

    shared_time = datetime(
        2026, 11, 1, 13, 0, 0,
        tzinfo=timezone.utc,
    )

    documents = [
        make_session(user_a, 1),
        make_session(user_a, 2),
        make_session(user_b, 99),
    ]

    for document in documents:
        document["created_at"] = shared_time

    database = {
        "recitation_sessions": FakeCollection(documents),
    }

    service = AuthenticatedService(user_a, database)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            first = client.get(
                "/api/v1/recitation/history?limit=1"
            )

            assert first.status_code == 200, first.text
            cursor = first.json()["next_cursor"]
            assert cursor is not None

            service.user_id = user_b

            response = client.get(
                "/api/v1/recitation/history",
                params={"cursor": cursor},
            )

            assert response.status_code == 200, response.text

            assert all(
                item["ayah_number"] != 1
                and item["ayah_number"] != 2
                for item in response.json()["items"]
            )

    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_empty_history_has_no_next_page():
    user_id = ObjectId()

    database = {
        "recitation_sessions": FakeCollection([]),
    }

    service = AuthenticatedService(user_id, database)
    app.dependency_overrides[get_auth_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/recitation/history"
            )

        assert response.status_code == 200, response.text
        assert response.json() == {
            "items": [],
            "count": 0,
            "has_more": False,
            "next_cursor": None,
        }

    finally:
        app.dependency_overrides.pop(get_auth_service, None)
