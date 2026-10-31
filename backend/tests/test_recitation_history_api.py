"""Tests for authenticated recitation history."""

from fastapi.testclient import TestClient

from app.api.v1.auth import get_auth_service
from app.main import app


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


from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId


class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def sort(self, field, direction):
        self.documents.sort(
            key=lambda doc: doc[field],
            reverse=direction == -1,
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
        return FakeCursor([
            doc for doc in self.documents
            if doc["user_id"] == query["user_id"]
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
