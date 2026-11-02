"""Tests for Halaqat MongoDB persistence."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.repositories.halaqat import HalaqatRepository
from bson import ObjectId


def make_repo():
    halaqat = MagicMock()
    enrollments = MagicMock()
    return HalaqatRepository({
        "halaqat": halaqat,
        "halaqa_enrollments": enrollments,
        "halaqa_sessions": MagicMock(),
        "halaqa_attendance": MagicMock(),
        "users": MagicMock(),
    }), halaqat, enrollments


def test_create_halaqa():
    repo, halaqat, _ = make_repo()
    halaqat.insert_one = AsyncMock()
    halaqat.insert_one.return_value.inserted_id = ObjectId()

    teacher_id = ObjectId()
    result = asyncio.run(repo.create_halaqa(
        name="Beginners",
        description="Level one",
        teacher_id=str(teacher_id),
    ))

    assert result["teacher_id"] == teacher_id
    assert result["status"] == "active"
    assert result["created_at"].microsecond % 1000 == 0
    halaqat.insert_one.assert_awaited_once()


def test_create_halaqa_rejects_invalid_teacher_id():
    repo, halaqat, _ = make_repo()
    halaqat.insert_one = AsyncMock()

    result = asyncio.run(repo.create_halaqa(
        name="Beginners",
        description=None,
        teacher_id="invalid",
    ))

    assert result is None
    halaqat.insert_one.assert_not_awaited()


def test_get_halaqa_invalid_id():
    repo, halaqat, _ = make_repo()
    halaqat.find_one = AsyncMock()

    assert asyncio.run(repo.get_halaqa("invalid")) is None
    halaqat.find_one.assert_not_awaited()


def test_get_halaqa_valid_id():
    repo, halaqat, _ = make_repo()
    halaqat.find_one = AsyncMock(return_value={"name": "Beginners"})
    identifier = ObjectId()

    result = asyncio.run(repo.get_halaqa(str(identifier)))

    assert result["name"] == "Beginners"
    halaqat.find_one.assert_awaited_once_with({"_id": identifier})


def test_enroll_student_uses_upsert():
    repo, _, enrollments = make_repo()
    enrollments.update_one = AsyncMock()
    enrollments.find_one = AsyncMock(return_value={"status": "active"})

    halaqa_id = ObjectId()
    student_id = ObjectId()

    result = asyncio.run(repo.enroll_student(
        halaqa_id=str(halaqa_id),
        student_id=str(student_id),
    ))

    assert result["status"] == "active"

    args = enrollments.update_one.await_args
    assert args.args[0] == {
        "halaqa_id": halaqa_id,
        "student_id": student_id,
    }
    assert args.kwargs["upsert"] is True
    assert args.args[1]["$set"]["status"] == "active"


def test_enroll_student_rejects_invalid_id():
    repo, _, enrollments = make_repo()
    enrollments.update_one = AsyncMock()

    result = asyncio.run(repo.enroll_student(
        halaqa_id="invalid",
        student_id=str(ObjectId()),
    ))

    assert result is None
    enrollments.update_one.assert_not_awaited()


def test_list_teacher_halaqat_is_scoped():
    repo, halaqat, _ = make_repo()
    teacher_id = ObjectId()

    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[{"name": "Beginners"}])
    halaqat.find.return_value = cursor

    result = asyncio.run(repo.list_teacher_halaqat(
        str(teacher_id),
        limit=20,
    ))

    assert len(result) == 1
    halaqat.find.assert_called_once_with({"teacher_id": teacher_id})
    cursor.limit.assert_called_once_with(20)


def test_list_enrollments_returns_active_only():
    repo, _, enrollments = make_repo()
    halaqa_id = ObjectId()

    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    student_id = ObjectId()
    cursor.to_list = AsyncMock(return_value=[
        {"student_id": student_id, "status": "active"}
    ])
    enrollments.find.return_value = cursor

    user_cursor = MagicMock()
    user_cursor.to_list = AsyncMock(return_value=[
        {"_id": student_id, "full_name": "Ahmed Mohamed"}
    ])
    repo.users.find.return_value = user_cursor

    result = asyncio.run(repo.list_enrollments(
        str(halaqa_id),
        limit=25,
    ))

    assert result[0]["student_name"] == "Ahmed Mohamed"

    assert len(result) == 1
    enrollments.find.assert_called_once_with({
        "halaqa_id": halaqa_id,
        "status": "active",
    })
    cursor.limit.assert_called_once_with(25)


def test_list_student_enrollments_invalid_id():
    import asyncio
    from unittest.mock import MagicMock

    from app.repositories.halaqat import HalaqatRepository

    database = MagicMock()
    repository = HalaqatRepository(database)

    result = asyncio.run(
        repository.list_student_enrollments("invalid-id")
    )

    assert result == []
    database["halaqa_enrollments"].find.assert_not_called()


def test_list_student_enrollments_filters_by_student():
    from unittest.mock import MagicMock

    from app.repositories.halaqat import HalaqatRepository
    from bson import ObjectId

    student_id = ObjectId()
    database = MagicMock()
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[])

    database["halaqa_enrollments"].find.return_value = cursor
    repository = HalaqatRepository(database)

    result = asyncio.run(
        repository.list_student_enrollments(str(student_id))
    )

    assert result == []
    database["halaqa_enrollments"].find.assert_called_once_with({
        "student_id": student_id,
        "status": "active",
    })
