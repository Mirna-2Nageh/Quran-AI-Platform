
"""Tests for memorization MongoDB persistence."""

import asyncio
from unittest.mock import AsyncMock

from app.repositories.memorization import MemorizationRepository
from bson import ObjectId


def test_create_plan():
    plans = AsyncMock()
    plans.insert_one.return_value.inserted_id = ObjectId()

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": AsyncMock(),
    })

    user_id = ObjectId()

    plan = asyncio.run(repo.create_plan(
        user_id=user_id,
        surah_number=2,
        start_ayah=1,
        end_ayah=20,
    ))

    assert plan["user_id"] == user_id
    assert plan["status"] == "active"
    assert plan["end_ayah"] == 20
    assert plan["created_at"].microsecond % 1000 == 0
    plans.insert_one.assert_awaited_once()


def test_get_plan_is_user_scoped():
    plans = AsyncMock()
    plans.find_one.return_value = None

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": AsyncMock(),
    })

    user_id = ObjectId()
    plan_id = str(ObjectId())

    result = asyncio.run(repo.get_plan(
        user_id=user_id,
        plan_id=plan_id,
    ))

    assert result is None
    plans.find_one.assert_awaited_once_with({
        "_id": ObjectId(plan_id),
        "user_id": user_id,
    })


def test_invalid_plan_id():
    plans = AsyncMock()

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": AsyncMock(),
    })

    result = asyncio.run(repo.get_plan(
        user_id=ObjectId(),
        plan_id="invalid-id",
    ))

    assert result is None
    plans.find_one.assert_not_awaited()

def test_create_session_rejects_unowned_plan():
    plans = AsyncMock()
    plans.find_one.return_value = None
    sessions = AsyncMock()

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": sessions,
    })

    user_id = ObjectId()
    plan_id = str(ObjectId())

    result = asyncio.run(repo.create_session(
        user_id=user_id,
        plan_id=plan_id,
        session_type="revision",
        result="completed",
    ))

    assert result is None
    plans.find_one.assert_awaited_once_with({
        "_id": ObjectId(plan_id),
        "user_id": user_id,
    })
    sessions.insert_one.assert_not_awaited()

def test_create_session_for_owned_plan():
    user_id = ObjectId()
    plan_id = ObjectId()
    session_id = ObjectId()

    plans = AsyncMock()
    plans.find_one.return_value = {
        "_id": plan_id,
        "user_id": user_id,
    }

    sessions = AsyncMock()
    sessions.insert_one.return_value.inserted_id = session_id

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": sessions,
    })

    session = asyncio.run(repo.create_session(
        user_id=user_id,
        plan_id=str(plan_id),
        session_type="revision",
        result="needs_review",
        notes="Review tomorrow",
    ))

    assert session["_id"] == session_id
    assert session["user_id"] == user_id
    assert session["plan_id"] == plan_id
    assert session["session_type"] == "revision"
    assert session["result"] == "needs_review"
    assert session["completed_at"].microsecond % 1000 == 0

    sessions.insert_one.assert_awaited_once()

def test_update_plan_is_user_scoped():
    user_id = ObjectId()
    plan_id = ObjectId()

    plans = AsyncMock()
    plans.find_one_and_update.return_value = {
        "_id": plan_id,
        "user_id": user_id,
        "status": "completed",
    }

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": AsyncMock(),
    })

    updated = asyncio.run(repo.update_plan(
        user_id=user_id,
        plan_id=str(plan_id),
        status="completed",
    ))

    assert updated["status"] == "completed"

    kwargs = plans.find_one_and_update.await_args
    assert kwargs.args[0] == {
        "_id": plan_id,
        "user_id": user_id,
    }
    assert kwargs.args[1]["$set"]["status"] == "completed"
    assert kwargs.args[1]["$set"]["updated_at"].microsecond % 1000 == 0
    plans.find_one_and_update.assert_awaited_once()

def test_list_plans_is_user_scoped():
    from unittest.mock import MagicMock

    user_id = ObjectId()
    plan_id = ObjectId()

    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[
        {"_id": plan_id, "user_id": user_id}
    ])

    plans = MagicMock()
    plans.find.return_value = cursor

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": AsyncMock(),
    })

    result = asyncio.run(repo.list_plans(
        user_id=user_id,
        limit=20,
    ))

    assert len(result) == 1
    plans.find.assert_called_once_with({"user_id": user_id})
    cursor.limit.assert_called_once_with(20)
    cursor.to_list.assert_awaited_once_with(length=20)

def test_list_sessions_is_user_scoped():
    from unittest.mock import MagicMock

    user_id = ObjectId()
    plan_id = ObjectId()

    plans = AsyncMock()
    plans.find_one.return_value = {
        "_id": plan_id,
        "user_id": user_id,
    }

    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[
        {"_id": ObjectId(), "plan_id": plan_id, "user_id": user_id}
    ])

    sessions = MagicMock()
    sessions.find.return_value = cursor

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": sessions,
    })

    result = asyncio.run(repo.list_sessions(
        user_id=user_id,
        plan_id=str(plan_id),
        limit=20,
    ))

    assert len(result) == 1
    sessions.find.assert_called_once_with({
        "user_id": user_id,
        "plan_id": plan_id,
    })
    cursor.to_list.assert_awaited_once_with(length=20)

def test_list_sessions_rejects_unowned_plan():
    user_id = ObjectId()
    plan_id = ObjectId()

    plans = AsyncMock()
    plans.find_one.return_value = None
    sessions = AsyncMock()

    repo = MemorizationRepository({
        "memorization_plans": plans,
        "memorization_sessions": sessions,
    })

    result = asyncio.run(repo.list_sessions(
        user_id=user_id,
        plan_id=str(plan_id),
    ))

    assert result is None
    plans.find_one.assert_awaited_once_with({
        "_id": plan_id,
        "user_id": user_id,
    })
    sessions.find.assert_not_called()


def test_count_revision_sessions():
    from unittest.mock import AsyncMock, MagicMock

    from app.repositories.memorization import MemorizationRepository

    database = MagicMock()
    repository = MemorizationRepository(database)
    repository.sessions.count_documents = AsyncMock(return_value=3)

    result = asyncio.run(
        repository.count_revision_sessions(user_id="user-1")
    )

    assert result == 3
    repository.sessions.count_documents.assert_awaited_once_with({
        "user_id": "user-1",
        "session_type": "revision",
    })
