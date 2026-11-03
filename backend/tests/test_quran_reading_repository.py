"""Quran reading repository tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.repositories.quran_reading import QuranReadingRepository


@pytest.mark.asyncio
async def test_add_bookmark_is_idempotent():
    database = MagicMock()
    collection = database.__getitem__.return_value
    collection.update_one = AsyncMock()
    collection.find_one = AsyncMock(
        return_value={
            "user_id": "user-a",
            "surah_number": 1,
            "ayah_number": 1,
        }
    )

    repo = QuranReadingRepository(database)

    first = await repo.add_bookmark("user-a", 1, 1)
    second = await repo.add_bookmark("user-a", 1, 1)

    assert first == second
    assert collection.update_one.await_count == 2

    for call in collection.update_one.await_args_list:
        assert call.kwargs["upsert"] is True
        assert call.args[0]["user_id"] == "user-a"
        assert "$setOnInsert" in call.args[1]


@pytest.mark.asyncio
async def test_remove_bookmark_is_user_scoped():
    database = MagicMock()
    collection = database.__getitem__.return_value
    collection.delete_one = AsyncMock()
    collection.delete_one.return_value.deleted_count = 1

    repo = QuranReadingRepository(database)
    deleted = await repo.remove_bookmark("user-a", 2, 5)

    assert deleted is True
    collection.delete_one.assert_awaited_once_with({
        "user_id": "user-a",
        "surah_number": 2,
        "ayah_number": 5,
    })


@pytest.mark.asyncio
async def test_save_progress_is_user_scoped():
    database = MagicMock()
    collection = database.__getitem__.return_value
    collection.update_one = AsyncMock()
    collection.find_one = AsyncMock(
        return_value={"surah_number": 2, "ayah_number": 5}
    )

    repo = QuranReadingRepository(database)
    result = await repo.save_progress("user-b", 2, 5)

    assert result["ayah_number"] == 5
    args = collection.update_one.await_args
    assert args.args[0] == {"user_id": "user-b"}
    assert args.kwargs["upsert"] is True
    assert args.args[1]["$set"]["surah_number"] == 2
    assert args.args[1]["$set"]["ayah_number"] == 5
