"""Tests for recitation session persistence."""

import asyncio
from unittest.mock import AsyncMock

from app.repositories.recitation_sessions import RecitationSessionRepository


def test_created_timestamp_has_millisecond_precision():
    repository = RecitationSessionRepository(
        {"recitation_sessions": object()}
    )

    timestamp = repository._current_timestamp()

    assert timestamp.tzinfo is not None
    assert timestamp.microsecond % 1000 == 0


def test_create_persists_millisecond_timestamp():
    from bson import ObjectId

    collection = AsyncMock()
    collection.insert_one.return_value.inserted_id = ObjectId()

    repository = RecitationSessionRepository(
        {"recitation_sessions": collection}
    )

    asyncio.run(
        repository.create(
            user_id=ObjectId(),
            surah_number=1,
            ayah_number=1,
            end_ayah_number=1,
            expected_text="بسم الله",
            recognized_text="بسم الله",
            alignment={"issues": []},
        )
    )

    document = collection.insert_one.await_args.args[0]

    assert document["created_at"].microsecond % 1000 == 0
