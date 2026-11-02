"""Business-rule tests for Halaqat sessions."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.halaqat import HalaqatService
from bson import ObjectId
from fastapi import HTTPException


def make_service(*, status="active", owner=True):
    teacher_id = ObjectId()
    halaqa_id = ObjectId()

    service = HalaqatService({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })

    service.repository.get_halaqa = AsyncMock(return_value={
        "_id": halaqa_id,
        "teacher_id": teacher_id if owner else ObjectId(),
        "status": status,
    })
    service.repository.create_session = AsyncMock(
        return_value={"_id": ObjectId()}
    )

    return service, {
        "_id": teacher_id,
        "role": "teacher",
        "is_active": True,
    }, str(halaqa_id)


def create(service, actor, halaqa_id, when):
    return asyncio.run(service.create_session(
        actor=actor,
        halaqa_id=halaqa_id,
        scheduled_at=when,
        duration_minutes=60,
        notes=None,
    ))


def test_session_creation_future_date():
    service, actor, halaqa_id = make_service()
    when = datetime.now(timezone.utc) + timedelta(days=2)

    create(service, actor, halaqa_id, when)

    service.repository.create_session.assert_awaited_once()


def test_session_rejects_past_date():
    service, actor, halaqa_id = make_service()
    when = datetime.now(timezone.utc) - timedelta(days=1)

    with pytest.raises(HTTPException) as exc:
        create(service, actor, halaqa_id, when)

    assert exc.value.status_code == 422
    service.repository.create_session.assert_not_awaited()


def test_session_rejects_naive_datetime():
    service, actor, halaqa_id = make_service()
    when = datetime.now(timezone.utc).replace(tzinfo=None)

    with pytest.raises(HTTPException) as exc:
        create(service, actor, halaqa_id, when)

    assert exc.value.status_code == 422
    service.repository.create_session.assert_not_awaited()


def test_session_rejects_paused_halaqa():
    service, actor, halaqa_id = make_service(status="paused")
    when = datetime.now(timezone.utc) + timedelta(days=2)

    with pytest.raises(HTTPException) as exc:
        create(service, actor, halaqa_id, when)

    assert exc.value.status_code == 409
    service.repository.create_session.assert_not_awaited()


def test_session_rejects_other_teacher():
    service, actor, halaqa_id = make_service(owner=False)
    when = datetime.now(timezone.utc) + timedelta(days=2)

    with pytest.raises(HTTPException) as exc:
        create(service, actor, halaqa_id, when)

    assert exc.value.status_code == 403
    service.repository.create_session.assert_not_awaited()


def test_session_listing_rejects_other_teacher():
    service, actor, halaqa_id = make_service(owner=False)
    service.repository.list_sessions = AsyncMock(return_value=[])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.list_sessions(
            actor=actor,
            halaqa_id=halaqa_id,
        ))

    assert exc.value.status_code == 403
    service.repository.list_sessions.assert_not_awaited()


def test_repository_creates_session():
    from types import SimpleNamespace

    from app.repositories.halaqat import HalaqatRepository

    sessions = MagicMock()
    session_id = ObjectId()
    sessions.insert_one = AsyncMock(
        return_value=SimpleNamespace(inserted_id=session_id)
    )

    repo = HalaqatRepository({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": sessions,
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })

    halaqa_id = ObjectId()
    when = datetime.now(timezone.utc) + timedelta(days=2)

    result = asyncio.run(repo.create_session(
        halaqa_id=str(halaqa_id),
        scheduled_at=when,
        duration_minutes=60,
        notes="Revision",
    ))

    assert result["_id"] == session_id
    assert result["halaqa_id"] == halaqa_id
    assert result["status"] == "scheduled"
    assert result["scheduled_at"] == when
    sessions.insert_one.assert_awaited_once()


def test_repository_lists_sessions_in_order():
    from app.repositories.halaqat import HalaqatRepository

    sessions = MagicMock()
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[])

    sessions.find.return_value = cursor

    repo = HalaqatRepository({
        "halaqat": MagicMock(),
        "halaqa_enrollments": MagicMock(),
        "halaqa_sessions": sessions,
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    })

    halaqa_id = ObjectId()
    result = asyncio.run(repo.list_sessions(str(halaqa_id)))

    assert result == []
    sessions.find.assert_called_once_with({
        "halaqa_id": halaqa_id
    })
    cursor.sort.assert_called_once_with([
        ("scheduled_at", 1),
        ("_id", 1),
    ])


def test_session_converts_timezone_to_utc():
    service, actor, halaqa_id = make_service()

    local_timezone = timezone(timedelta(hours=2))
    scheduled = datetime.now(local_timezone) + timedelta(days=2)

    create(service, actor, halaqa_id, scheduled)

    kwargs = service.repository.create_session.await_args.kwargs
    stored = kwargs["scheduled_at"]

    assert stored.utcoffset() == timedelta(0)
    assert stored == scheduled.astimezone(timezone.utc)
    assert kwargs["duration_minutes"] == 60
