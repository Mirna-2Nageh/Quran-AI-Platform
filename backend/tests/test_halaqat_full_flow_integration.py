"""Real MongoDB enrollment-to-attendance integration test."""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
from app.services.halaqat import HalaqatService
from bson import ObjectId
from fastapi import HTTPException
from pymongo import AsyncMongoClient


def test_enrollment_attendance_student_history():
    async def run():
        uri = os.environ.get("QURAN_AI_TEST_MONGO_URI", "")

        if not uri:
            pytest.skip("MongoDB test URI is not configured")

        assert os.environ["QURAN_AI_ENVIRONMENT"] == "testing"
        assert os.environ["QURAN_AI_MONGO_DB_NAME"] == "quran_ai_ci_test"

        client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client["quran_ai_ci_test"]

        halaqa_id = ObjectId()
        teacher_id = ObjectId()
        student_id = ObjectId()
        session_id = ObjectId()

        teacher = {
            "_id": teacher_id,
            "role": "teacher",
            "is_active": True,
        }
        student = {
            "_id": student_id,
            "role": "student",
            "is_active": True,
        }

        try:
            await client.admin.command("ping")

            await db["halaqa_enrollments"].create_index(
                [("halaqa_id", 1), ("student_id", 1)],
                unique=True,
            )
            await db["halaqa_attendance"].create_index(
                [("session_id", 1), ("student_id", 1)],
                unique=True,
            )

            await db["halaqat"].insert_one({
                "_id": halaqa_id,
                "name": "Integration Test Halaqa",
                "description": "Temporary test",
                "teacher_id": teacher_id,
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })

            await db["users"].insert_one({
                "_id": student_id,
                "full_name": "Integration Test Student",
                "email": f"test-{student_id}@example.com",
                "role": "student",
                "is_active": True,
            })

            service = HalaqatService(db)

            enrollment = await service.enroll_student(
                actor=teacher,
                halaqa_id=str(halaqa_id),
                student_id=str(student_id),
            )
            assert enrollment["status"] == "active"

            await db["halaqa_sessions"].insert_one({
                "_id": session_id,
                "halaqa_id": halaqa_id,
                "scheduled_at": datetime.now(timezone.utc)
                + timedelta(hours=2),
                "duration_minutes": 60,
                "notes": "Integration test",
                "status": "scheduled",
            })

            async def record(status):
                return await service.record_attendance(
                    actor=teacher,
                    session_id=str(session_id),
                    student_id=str(student_id),
                    status=status,
                    notes=None,
                )

            with pytest.raises(HTTPException) as exc:
                await record("present")
            assert exc.value.status_code == 409

            await db["halaqa_sessions"].update_one(
                {"_id": session_id},
                {"$set": {
                    "scheduled_at": datetime.now(timezone.utc)
                    - timedelta(hours=1),
                }},
            )

            first = await record("present")
            assert first["status"] == "present"

            second = await record("late")
            assert second["_id"] == first["_id"]
            assert second["status"] == "late"

            history = await service.list_my_attendance(actor=student)

            assert any(
                item["_id"] == first["_id"]
                and item["status"] == "late"
                for item in history
            )

            assert await db["halaqa_attendance"].count_documents({
                "session_id": session_id,
                "student_id": student_id,
            }) == 1

        finally:
            await db["halaqa_attendance"].delete_many({
                "session_id": session_id,
                "student_id": student_id,
            })
            await db["halaqa_sessions"].delete_one({"_id": session_id})
            await db["halaqa_enrollments"].delete_many({
                "halaqa_id": halaqa_id,
                "student_id": student_id,
            })
            await db["halaqat"].delete_one({"_id": halaqa_id})
            await db["users"].delete_one({"_id": student_id})
            await client.close()

    asyncio.run(run())
