"""Real MongoDB integration test for live recitation finalization."""

import os
from uuid import uuid4

import pytest
from app.repositories.live_recitation_sessions import (
    LiveRecitationSessionRepository,
)
from pymongo import AsyncMongoClient


@pytest.mark.asyncio
async def test_real_live_finalization():
    uri = os.environ["QURAN_AI_TEST_MONGO_URI"]
    client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
    database = client["quran_ai_ci_test"]
    suffix = uuid4().hex
    live_name = "test_live_" + suffix
    history_name = "test_history_" + suffix
    repository = LiveRecitationSessionRepository(
        database,
        live_collection=live_name,
        history_collection=history_name,
    )

    try:
        live = await repository.create(
            user_id="test-user",
            surah_number=1,
            ayah_number=1,
            expected_text="بسم الله الرحمن الرحيم",
        )
        await repository.append_chunk(
            user_id="test-user",
            session_id=live["session_id"],
            chunk={"recognized_text": "بسم الله الرحمن الرحيم"},
        )

        first = await repository.finalize_atomic(
            client=client,
            user_id="test-user",
            session_id=live["session_id"],
        )
        second = await repository.finalize_atomic(
            client=client,
            user_id="test-user",
            session_id=live["session_id"],
        )

        assert first == second
        assert await database[history_name].count_documents({}) == 1
    finally:
        await database[live_name].drop()
        await database[history_name].drop()
        await client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_real_live_finalization())
    print("REAL LIVE FINALIZATION: PASSED")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_real_live_finalization())
    print("REAL LIVE FINALIZATION: PASSED")


@pytest.mark.asyncio
async def test_concurrent_finalization():
    import asyncio

    uri = os.environ["QURAN_AI_TEST_MONGO_URI"]
    client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
    database = client["quran_ai_ci_test"]
    suffix = uuid4().hex
    live_name = "test_live_" + suffix
    history_name = "test_history_" + suffix
    repository = LiveRecitationSessionRepository(
        database, live_collection=live_name, history_collection=history_name
    )
    try:
        live = await repository.create(
            user_id="concurrent-test",
            surah_number=1,
            ayah_number=1,
            expected_text="بسم الله الرحمن الرحيم",
        )
        await repository.append_chunk(
            user_id="concurrent-test",
            session_id=live["session_id"],
            chunk={"recognized_text": "بسم الله الرحمن الرحيم"},
        )
        results = await asyncio.gather(
            *[
                repository.finalize_atomic(
                    client=client,
                    user_id="concurrent-test",
                    session_id=live["session_id"],
                )
                for _ in range(2)
            ],
            return_exceptions=True,
        )
        count = await database[history_name].count_documents({})
        assert count == 1, f"Duplicate records: {count}"
        assert all(not isinstance(r, Exception) for r in results), results
        assert results[0] == results[1]
    finally:
        await database[live_name].drop()
        await database[history_name].drop()
        await client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_concurrent_finalization())
    print("CONCURRENT LIVE FINALIZATION: PASSED")
