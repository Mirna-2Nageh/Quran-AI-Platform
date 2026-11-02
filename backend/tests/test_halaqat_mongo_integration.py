"""Real MongoDB integration tests for Halaqat attendance."""

import asyncio

from app.repositories.halaqat import HalaqatRepository
from bson import ObjectId
from pymongo import AsyncMongoClient


def test_halaqat_attendance_real_mongodb():
    async def run():
        import os

        import pytest

        uri = os.environ.get("QURAN_AI_TEST_MONGO_URI", "")
        if not uri:
            pytest.skip("MongoDB test URI is not configured")

        if os.environ.get("QURAN_AI_ENVIRONMENT") != "testing":
            pytest.fail("Testing environment required")

        if os.environ.get("QURAN_AI_MONGO_DB_NAME") != "quran_ai_ci_test":
            pytest.fail("Refusing non-test database")

        client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
        database = client["quran_ai_ci_test"]

        session_id = ObjectId()
        student_id = ObjectId()
        teacher_id = ObjectId()

        try:
            await client.admin.command("ping")

            await database["halaqa_attendance"].create_index(
                [("session_id", 1), ("student_id", 1)],
                unique=True,
            )

            repo = HalaqatRepository(database)

            first = await repo.upsert_attendance(
                session_id=str(session_id),
                student_id=str(student_id),
                status="present",
                notes="integration-test",
                recorded_by=str(teacher_id),
            )

            assert first["status"] == "present"
            assert first["student_id"] == student_id

            second = await repo.upsert_attendance(
                session_id=str(session_id),
                student_id=str(student_id),
                status="late",
                notes="updated-integration-test",
                recorded_by=str(teacher_id),
            )

            assert second["_id"] == first["_id"]
            assert second["status"] == "late"
            assert second["created_at"] == first["created_at"]

            count = await database["halaqa_attendance"].count_documents(
                {"session_id": session_id, "student_id": student_id}
            )
            assert count == 1

            session_records = await repo.list_session_attendance(
                str(session_id)
            )
            assert len(session_records) == 1
            assert session_records[0]["status"] == "late"

            student_records = await repo.list_student_attendance(
                str(student_id)
            )
            assert any(
                record["_id"] == first["_id"]
                for record in student_records
            )

            print("\nREAL MONGODB HALAQAT ATTENDANCE: PASSED")

        finally:
            await database["halaqa_attendance"].delete_many(
                {"session_id": session_id, "student_id": student_id}
            )
            await client.close()

    asyncio.run(run())


def test_halaqat_attendance_unique_index_real_mongodb():
    import os

    import pytest
    from pymongo.errors import DuplicateKeyError

    async def run():
        uri = os.environ.get("QURAN_AI_TEST_MONGO_URI", "")
        if not uri:
            pytest.skip("MongoDB test URI is not configured")

        if os.environ.get("QURAN_AI_ENVIRONMENT") != "testing":
            pytest.fail("Testing environment required")

        if os.environ.get("QURAN_AI_MONGO_DB_NAME") != "quran_ai_ci_test":
            pytest.fail("Refusing non-test database")

        client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
        collection = client["quran_ai_ci_test"]["halaqa_attendance"]

        session_id = ObjectId()
        student_id = ObjectId()

        query = {
            "session_id": session_id,
            "student_id": student_id,
        }

        try:
            await collection.create_index(
                [("session_id", 1), ("student_id", 1)],
                unique=True,
            )

            await collection.insert_one({
                **query,
                "status": "present",
            })

            with pytest.raises(DuplicateKeyError):
                await collection.insert_one({
                    **query,
                    "status": "late",
                })

            assert await collection.count_documents(query) == 1

        finally:
            await collection.delete_many(query)
            await client.close()

    asyncio.run(run())
