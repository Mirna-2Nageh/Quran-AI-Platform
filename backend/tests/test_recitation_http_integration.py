"""HTTP integration test using a real MongoDB database."""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from app.api.v1.auth import get_auth_service
from app.config import Settings
from app.main import app
from app.services.quran_asr import ASRMetadata
from app.services.quran_text import get_quran_text
from pymongo import AsyncMongoClient

WEBM = b"\x1a\x45\xdf\xa3" + b"test-audio-data"
EXPECTED = get_quran_text(1, 1, 1)


def test_recitation_save_history_and_user_isolation():

    async def run():
        settings = Settings()

        if not settings.mongo_uri:
            pytest.skip("MongoDB test URI is not configured")

        if settings.environment != "testing":
            pytest.fail("Integration tests require the testing environment")

        if settings.mongo_db_name != "quran_ai_ci_test":
            pytest.fail("Refusing to use a non-test MongoDB database")

        client = AsyncMongoClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=5000,
        )

        database = client[settings.mongo_db_name]

        owner_id = f"recitation-test-{uuid4().hex}"
        other_id = f"other-test-{uuid4().hex}"

        service = AsyncMock()
        service.database = database
        service.get_current_user.return_value = {
            "_id": owner_id
        }
        service.verify_csrf.return_value = True

        previous_override = app.dependency_overrides.get(
            get_auth_service
        )

        app.dependency_overrides[get_auth_service] = (
            lambda: service
        )

        try:
            transport = httpx.ASGITransport(app=app)

            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                cookies={
                    "quran_session": "integration-test-session"
                },
            ) as http:

                with patch(
                    "app.api.v1.audio_analysis.transcribe_audio_with_metadata",
                    new_callable=AsyncMock,
                    return_value=ASRMetadata(
                        text=EXPECTED,
                        tokens=[],
                        timestamps=[],
                        timing_type="asr_character_token_timestamps",
                    ),
                ):
                    response = await http.post(
                        "/api/v1/recitation/analyze",
                        data={
                            "expected_text": EXPECTED,
                            "surah_number": 1,
                            "ayah_number": 1,
                        },
                        files={
                            "audio": (
                                "recitation.webm",
                                WEBM,
                                "audio/webm",
                            )
                        },
                        headers={
                            "X-CSRF-Token": "test-csrf"
                        },
                    )

                assert response.status_code == 200, response.text

                saved_id = response.json()["session_id"]

                print("\nSAVE VIA HTTP: PASSED")

                history = await http.get(
                    "/api/v1/recitation/history"
                )

                assert history.status_code == 200, history.text

                assert any(
                    item["id"] == saved_id
                    for item in history.json()["items"]
                )

                print("OWNER HISTORY VIA HTTP: PASSED")

                service.get_current_user.return_value = {
                    "_id": other_id
                }

                other_history = await http.get(
                    "/api/v1/recitation/history"
                )

                assert other_history.status_code == 200

                assert all(
                    item["id"] != saved_id
                    for item in other_history.json()["items"]
                )

                print("USER ISOLATION VIA HTTP: PASSED")

        finally:
            if previous_override is None:
                app.dependency_overrides.pop(
                    get_auth_service, None
                )
            else:
                app.dependency_overrides[
                    get_auth_service
                ] = previous_override

            try:
                result = await database[
                    "recitation_sessions"
                ].delete_many({
                    "user_id": owner_id
                })

                print(
                    "CLEANUP:",
                    result.deleted_count,
                    "test session(s) deleted",
                )
            finally:
                await client.close()

    asyncio.run(run())


def test_recitation_history_cursor_pagination_real_mongodb():
    """Verify pagination against real MongoDB, not a fake collection."""
    from datetime import datetime, timedelta, timezone

    from app.repositories.recitation_sessions import RecitationSessionRepository

    async def run():
        settings = Settings()

        if not settings.mongo_uri:
            pytest.skip("MongoDB test URI is not configured")

        if settings.environment != "testing":
            pytest.fail("Integration tests require testing environment")

        if settings.mongo_db_name != "quran_ai_ci_test":
            pytest.fail("Refusing non-test MongoDB database")

        client = AsyncMongoClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=5000,
        )
        database = client[settings.mongo_db_name]

        owner_id = f"pagination-owner-{uuid4().hex}"
        other_id = f"pagination-other-{uuid4().hex}"

        service = AsyncMock()
        service.database = database
        service.get_current_user.return_value = {"_id": owner_id}

        previous_override = app.dependency_overrides.get(
            get_auth_service
        )
        app.dependency_overrides[get_auth_service] = lambda: service

        collection = database["recitation_sessions"]
        inserted_ids = []

        try:
            repository = RecitationSessionRepository(database)

            for number in range(1, 6):
                document = await repository.create(
                    user_id=owner_id,
                    surah_number=1,
                    ayah_number=number,
                    end_ayah_number=number,
                    expected_text=EXPECTED,
                    recognized_text=EXPECTED,
                    alignment={"issues": []},
                )
                inserted_ids.append(document["_id"])

            shared_time = datetime(
                2026, 11, 1, 13, 0, 0,
                tzinfo=timezone.utc,
            )

            for index, document_id in enumerate(inserted_ids):
                timestamp = (
                    shared_time
                    if index < 3
                    else shared_time - timedelta(minutes=index)
                )
                await collection.update_one(
                    {"_id": document_id},
                    {"$set": {"created_at": timestamp}},
                )

            other_document = await repository.create(
                user_id=other_id,
                surah_number=1,
                ayah_number=99,
                end_ayah_number=99,
                expected_text=EXPECTED,
                recognized_text=EXPECTED,
                alignment={"issues": []},
            )
            inserted_ids.append(other_document["_id"])

            transport = httpx.ASGITransport(app=app)

            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                cookies={"quran_session": "pagination-test"},
            ) as http:
                all_items = []
                cursor = None

                for page_number in range(3):
                    params = {"limit": 2}
                    if cursor:
                        params["cursor"] = cursor

                    response = await http.get(
                        "/api/v1/recitation/history",
                        params=params,
                    )

                    assert response.status_code == 200, response.text
                    data = response.json()

                    all_items.extend(data["items"])

                    if page_number < 2:
                        assert data["has_more"] is True
                        assert data["next_cursor"] is not None
                    else:
                        assert data["has_more"] is False
                        assert data["next_cursor"] is None

                    if page_number == 0:
                        first_page_cursor = data["next_cursor"]

                    cursor = data["next_cursor"]

                assert len(all_items) == 5

                returned_ids = [item["id"] for item in all_items]
                assert len(set(returned_ids)) == 5
                assert set(returned_ids) == {
                    str(value) for value in inserted_ids[:5]
                }

                expected_order = [
                    str(value) for value in sorted(
                        inserted_ids[:3], reverse=True
                    )
                ]
                assert returned_ids[:3] == expected_order

                invalid = await http.get(
                    "/api/v1/recitation/history",
                    params={"cursor": "invalid!"},
                )
                assert invalid.status_code == 422

                service.get_current_user.return_value = {
                    "_id": other_id
                }

                other_history = await http.get(
                    "/api/v1/recitation/history",
                    params={"limit": 2},
                )
                assert other_history.status_code == 200
                assert [
                    item["id"] for item in other_history.json()["items"]
                ] == [str(other_document["_id"])]

                # A cursor from another user must not expose owner data.
                cross_user = await http.get(
                    "/api/v1/recitation/history",
                    params={
                        "limit": 2,
                        "cursor": (
                            first_page_cursor
                        ),
                    },
                )
                assert cross_user.status_code == 200, cross_user.text
                assert cross_user.json()["items"] == []
                assert cross_user.json()["has_more"] is False
                assert cross_user.json()["next_cursor"] is None

                # A user with no sessions gets an empty page.
                service.get_current_user.return_value = {
                    "_id": f"empty-user-{uuid4().hex}"
                }
                empty = await http.get(
                    "/api/v1/recitation/history"
                )
                assert empty.status_code == 200, empty.text
                assert empty.json() == {
                    "items": [],
                    "count": 0,
                    "has_more": False,
                    "next_cursor": None,
                }

                print("REAL MONGODB PAGINATION: PASSED")

        finally:
            if previous_override is None:
                app.dependency_overrides.pop(
                    get_auth_service, None
                )
            else:
                app.dependency_overrides[get_auth_service] = previous_override

            try:
                await collection.delete_many(
                    {"user_id": {"$in": [owner_id, other_id]}}
                )
            finally:
                await client.close()

    asyncio.run(run())
