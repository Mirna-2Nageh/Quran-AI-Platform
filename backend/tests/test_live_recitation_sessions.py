"""Tests for persistent live recitation sessions."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.repositories.live_recitation_sessions import (
    LiveRecitationSessionRepository,
)


@pytest.fixture
def repository():
    database = MagicMock()
    database["live_recitation_sessions"].find_one = AsyncMock()
    database["live_recitation_sessions"].update_one = AsyncMock()
    database["recitation_sessions"].insert_one = AsyncMock()
    return LiveRecitationSessionRepository(database)


@pytest.mark.asyncio
async def test_finalize_missing_session(repository):
    repository.collection.find_one.return_value = None

    async def execute(_client, operation):
        return await operation(MagicMock())

    with patch(
        "app.repositories.memorization_transactions.run_transaction",
        side_effect=execute,
    ):
        result = await repository.finalize_atomic(
            client=MagicMock(),
            user_id="user-1",
            session_id="missing",
        )

    assert result is None
    repository.database["recitation_sessions"].insert_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_finalize_creates_recitation_once(repository):
    live = {
        "_id": "live-db-id",
        "session_id": "live-1",
        "user_id": "user-1",
        "status": "active",
        "surah_number": 1,
        "ayah_number": 1,
        "expected_text": "بسم الله الرحمن الرحيم",
        "chunks": [
            {"recognized_text": "بسم الله"},
            {"recognized_text": "الرحمن الرحيم"},
        ],
    }
    repository.collection.find_one.return_value = live
    repository.database[
        "recitation_sessions"
    ].insert_one.return_value = SimpleNamespace(inserted_id="saved-1")
    repository.collection.update_one.return_value = SimpleNamespace(matched_count=1)

    async def execute(_client, operation):
        return await operation(MagicMock())

    with patch(
        "app.repositories.memorization_transactions.run_transaction",
        side_effect=execute,
    ):
        result = await repository.finalize_atomic(
            client=MagicMock(),
            user_id="user-1",
            session_id="live-1",
        )

    assert result == "saved-1"
    repository.database["recitation_sessions"].insert_one.assert_awaited_once()
    repository.collection.update_one.assert_awaited_once()

    saved_document = repository.database[
        "recitation_sessions"
    ].insert_one.await_args.args[0]
    assert saved_document["recognized_text"] == ("بسم الله الرحمن الرحيم")
    assert saved_document["alignment"]["matched_word_count"] == 4


@pytest.mark.asyncio
async def test_finalize_retry_returns_existing_session(repository):
    repository.collection.find_one.return_value = {
        "status": "finalized",
        "recitation_session_id": "saved-1",
    }

    async def execute(_client, operation):
        return await operation(MagicMock())

    with patch(
        "app.repositories.memorization_transactions.run_transaction",
        side_effect=execute,
    ):
        result = await repository.finalize_atomic(
            client=MagicMock(),
            user_id="user-1",
            session_id="live-1",
        )

    assert result == "saved-1"
    repository.database["recitation_sessions"].insert_one.assert_not_awaited()
    repository.collection.update_one.assert_not_awaited()
