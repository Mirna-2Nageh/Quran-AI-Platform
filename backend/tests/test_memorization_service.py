"""Tests for memorization business logic."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.services.memorization import MemorizationService
from app.services.quran_text import QuranTextError


def test_create_valid_plan():
    repository = AsyncMock()
    repository.create_plan.return_value = {"status": "active"}
    service = MemorizationService(repository)

    result = asyncio.run(
        service.create_plan(
            user_id="user-1",
            surah_number=1,
            start_ayah=1,
            end_ayah=7,
        )
    )

    assert result["status"] == "active"
    repository.create_plan.assert_awaited_once_with(
        user_id="user-1",
        surah_number=1,
        start_ayah=1,
        end_ayah=7,
    )


def test_invalid_range_does_not_write_to_database():
    repository = AsyncMock()
    service = MemorizationService(repository)

    with pytest.raises(QuranTextError):
        asyncio.run(
            service.create_plan(
                user_id="user-1",
                surah_number=1,
                start_ayah=1,
                end_ayah=100,
            )
        )

    repository.create_plan.assert_not_awaited()


def test_get_plan_delegates_to_repository():
    repository = AsyncMock()
    repository.get_plan.return_value = {"status": "active"}
    service = MemorizationService(repository)

    result = asyncio.run(service.get_plan(user_id="u1", plan_id="p1"))

    assert result["status"] == "active"
    repository.get_plan.assert_awaited_once_with(user_id="u1", plan_id="p1")


def test_list_plans_delegates_to_repository():
    repository = AsyncMock()
    repository.list_plans.return_value = []
    service = MemorizationService(repository)

    result = asyncio.run(service.list_plans(user_id="u1", limit=10))

    assert result == []
    repository.list_plans.assert_awaited_once_with(user_id="u1", limit=10)


def test_update_plan_delegates_to_repository():
    repository = AsyncMock()
    repository.update_plan_atomic.return_value = {"status": "completed"}
    service = MemorizationService(repository)

    result = asyncio.run(
        service.update_plan(user_id="u1", plan_id="p1", status="completed")
    )

    assert result["status"] == "completed"
    repository.update_plan_atomic.assert_awaited_once_with(
        user_id="u1",
        plan_id="p1",
        status="completed",
        surah_number=None,
        start_ayah=None,
        end_ayah=None,
    )


def test_create_session_delegates():
    repository = AsyncMock()
    repository.create_session_atomic.return_value = {"result": "completed"}
    service = MemorizationService(repository)

    result = asyncio.run(
        service.create_session(
            user_id="u1",
            plan_id="p1",
            session_type="revision",
            result="completed",
            notes="Reviewed successfully",
        )
    )

    assert result["result"] == "completed"
    repository.create_session_atomic.assert_awaited_once_with(
        user_id="u1",
        plan_id="p1",
        session_type="revision",
        result="completed",
        notes="Reviewed successfully",
    )


def test_list_sessions_delegates():
    repository = AsyncMock()
    repository.list_sessions.return_value = []
    service = MemorizationService(repository)

    result = asyncio.run(service.list_sessions(user_id="u1", plan_id="p1", limit=10))

    assert result == []
    repository.list_sessions.assert_awaited_once_with(
        user_id="u1", plan_id="p1", limit=10
    )


def test_get_progress_calculates_user_plans():
    repository = AsyncMock()
    repository.list_all_plans_for_progress.return_value = [
        {
            "surah_number": 1,
            "start_ayah": 1,
            "end_ayah": 7,
            "status": "completed",
        },
        {
            "surah_number": 2,
            "start_ayah": 1,
            "end_ayah": 3,
            "status": "active",
        },
    ]
    repository.count_revision_sessions.return_value = 3
    service = MemorizationService(repository)

    result = asyncio.run(service.get_progress(user_id="u1"))

    assert result["total_plans"] == 2
    assert result["completed_ayahs"] == 7
    assert result["unique_planned_ayahs"] == 10
    assert result["completion_rate"] == 70.0
    assert result["revision_sessions"] == 3
    repository.list_all_plans_for_progress.assert_awaited_once_with(user_id="u1")

    repository.count_revision_sessions.assert_awaited_once_with(user_id="u1")
