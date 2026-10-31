"""HTTP integration test using a real MongoDB database."""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from pymongo import AsyncMongoClient

from app.services.quran_text import get_quran_text
from app.services.quran_asr import ASRMetadata
from app.api.v1.auth import get_auth_service
from app.config import Settings
from app.main import app


WEBM = b"\x1a\x45\xdf\xa3" + b"test-audio-data"
EXPECTED = get_quran_text(1, 1, 1)


def test_recitation_save_history_and_user_isolation():

    async def run():
        settings = Settings()

        if not settings.mongo_uri:
            pytest.skip("MongoDB URI is not configured")

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
                    return_value=ASRMetadata(text=EXPECTED, tokens=[], timestamps=[], timing_type="asr_character_token_timestamps"),
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
