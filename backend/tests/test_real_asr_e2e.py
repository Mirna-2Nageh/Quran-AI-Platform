"""Real ASR + HTTP + MongoDB end-to-end integration test."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock
from urllib.parse import quote
from uuid import uuid4

import httpx
import pytest
from app.api.v1.auth import get_auth_service
from app.config import Settings
from app.main import app
from app.services.quran_text import get_quran_text
from pymongo import AsyncMongoClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIO_PATH = PROJECT_ROOT / "tests/audio_samples/fatiha_reference.webm"
TEST_ENV_PATH = PROJECT_ROOT / ".env.mongo.test"
TEST_DATABASE = "quran_ai_ci_test"


def get_test_mongo_uri() -> str:
    if not TEST_ENV_PATH.is_file():
        pytest.skip("Local MongoDB test credentials are unavailable")

    values = dict(
        line.split("=", 1)
        for line in TEST_ENV_PATH.read_text().splitlines()
        if "=" in line
    )

    if values.get("MONGO_TEST_DATABASE") != TEST_DATABASE:
        pytest.fail("Refusing to connect to a non-test database")

    username = quote(values["MONGO_TEST_USERNAME"], safe="")
    password = quote(values["MONGO_TEST_PASSWORD"], safe="")

    return (
        f"mongodb://{username}:{password}"
        f"@127.0.0.1:27018/{TEST_DATABASE}"
        f"?authSource={TEST_DATABASE}"
    )


@pytest.mark.real_asr
def test_real_audio_analysis_http_mongodb():
    """Verify real inference, HTTP response and persisted session."""

    settings = Settings()

    if settings.environment != "testing":
        pytest.fail("Real E2E requires QURAN_AI_ENVIRONMENT=testing")

    if not AUDIO_PATH.is_file():
        pytest.skip("Real audio sample is missing")

    mongo_uri = get_test_mongo_uri()
    expected_text = get_quran_text(1, 1, 1)

    async def run():
        mongo = AsyncMongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
        )
        database = mongo[TEST_DATABASE]
        user_id = f"real-asr-e2e-{uuid4().hex}"

        auth_service = AsyncMock()
        auth_service.database = database
        auth_service.get_current_user.return_value = {
            "_id": user_id,
        }
        auth_service.verify_csrf.return_value = True

        previous_override = app.dependency_overrides.get(
            get_auth_service
        )

        app.dependency_overrides[get_auth_service] = (
            lambda: auth_service
        )

        try:
            transport = httpx.ASGITransport(app=app)

            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                cookies={
                    "quran_session": "real-e2e-test-session",
                },
                timeout=120.0,
            ) as http:
                response = await http.post(
                    "/api/v1/recitation/analyze",
                    data={
                        "expected_text": expected_text,
                        "surah_number": 1,
                        "ayah_number": 1,
                    },
                    files={
                        "audio": (
                            AUDIO_PATH.name,
                            AUDIO_PATH.read_bytes(),
                            "audio/webm",
                        ),
                    },
                    headers={
                        "X-CSRF-Token": "test-csrf",
                    },
                )

                assert response.status_code == 200, response.text

                payload = response.json()

                assert payload["session_id"]
                assert payload["recognized_text"].strip()
                assert payload["analysis_type"] == (
                    "word_level_asr_alignment"
                )
                assert payload["tajweed_analyzed"] is False
                assert isinstance(payload["word_timings"], list)
                assert len(payload["word_timings"]) > 0

                saved = await database[
                    "recitation_sessions"
                ].find_one({
                    "user_id": user_id,
                })

                assert saved is not None
                assert saved["recognized_text"] == (
                    payload["recognized_text"]
                )
                assert str(saved["_id"]) == payload["session_id"]

                print("\nREAL HTTP + ASR + MONGODB: PASSED")
                print("Recognized text:", payload["recognized_text"])
                print("Word timings:", len(payload["word_timings"]))
                print("Session persisted: YES")

        finally:
            if previous_override is None:
                app.dependency_overrides.pop(
                    get_auth_service,
                    None,
                )
            else:
                app.dependency_overrides[
                    get_auth_service
                ] = previous_override

            try:
                result = await database[
                    "recitation_sessions"
                ].delete_many({
                    "user_id": user_id,
                })
                print(
                    "Cleanup:",
                    result.deleted_count,
                    "test session(s)",
                )
            finally:
                await mongo.close()

    asyncio.run(run())
