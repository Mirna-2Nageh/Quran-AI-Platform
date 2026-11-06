"""Tests for atomic memorization plan updates."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.repositories.memorization import MemorizationRepository
from app.services.quran_text import QuranTextError
from bson import ObjectId

from tests.memorization_transaction_mocks import configure_transaction


def make_repository(status="active", session_count=0):
    db = MagicMock()
    session = configure_transaction(db)
    plan_id = ObjectId()

    plans = db["memorization_plans"]
    sessions = db["memorization_sessions"]

    plan = {
        "_id": plan_id,
        "user_id": "u1",
        "status": status,
        "surah_number": 1,
        "start_ayah": 1,
        "end_ayah": 7,
    }

    plans.find_one = AsyncMock(return_value=plan)
    plans.find_one_and_update = AsyncMock(return_value=plan)
    sessions.count_documents = AsyncMock(return_value=session_count)

    return MemorizationRepository(db), plans, sessions, session, str(plan_id)


def test_edit_plan_range_success():
    repo, plans, sessions, session, plan_id = make_repository()

    result = asyncio.run(repo.update_plan_atomic(
        user_id="u1",
        plan_id=plan_id,
        surah_number=2,
        start_ayah=1,
        end_ayah=10,
    ))

    assert result is not None
    plans.find_one_and_update.assert_awaited_once()
    args, kwargs = plans.find_one_and_update.await_args

    assert args[1]["$set"]["surah_number"] == 2
    assert args[1]["$set"]["end_ayah"] == 10
    assert args[1]["$inc"]["revision"] == 1
    assert kwargs["session"] is session
    sessions.count_documents.assert_awaited_once()
    session.commit_transaction.assert_awaited_once()


def test_edit_plan_rejected_when_sessions_exist():
    repo, plans, _, _, plan_id = make_repository(session_count=1)

    with pytest.raises(ValueError, match="sessions exist"):
        asyncio.run(repo.update_plan_atomic(
            user_id="u1",
            plan_id=plan_id,
            end_ayah=5,
        ))

    plans.find_one_and_update.assert_not_awaited()


def test_edit_plan_rejects_invalid_quran_range():
    repo, plans, _, _, plan_id = make_repository()

    with pytest.raises(QuranTextError):
        asyncio.run(repo.update_plan_atomic(
            user_id="u1",
            plan_id=plan_id,
            end_ayah=100,
        ))

    plans.find_one_and_update.assert_not_awaited()


def test_archived_plan_cannot_edit_range():
    repo, plans, _, _, plan_id = make_repository(status="archived")

    with pytest.raises(ValueError, match="Archived"):
        asyncio.run(repo.update_plan_atomic(
            user_id="u1",
            plan_id=plan_id,
            end_ayah=5,
        ))

    plans.find_one_and_update.assert_not_awaited()
