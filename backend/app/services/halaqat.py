"""Business rules and permissions for Halaqat."""

from bson import ObjectId
from fastapi import HTTPException

from app.repositories.halaqat import HalaqatRepository
from app.repositories.users import UserRepository


class HalaqatService:
    def __init__(self, database):
        self.repository = HalaqatRepository(database)
        self.users = UserRepository(database)

    @staticmethod
    def parse_id(value):
        if not ObjectId.is_valid(value):
            raise HTTPException(status_code=422, detail="Invalid ID")
        return ObjectId(value)

    @staticmethod
    def require_admin(actor):
        if actor.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin required")

    async def create_halaqa(
        self, *, actor, name, description, teacher_id
    ):
        self.require_admin(actor)

        teacher = await self.users.get_by_id(
            self.parse_id(teacher_id)
        )

        if (
            teacher is None
            or teacher.get("role") != "teacher"
            or not teacher.get("is_active", False)
        ):
            raise HTTPException(
                status_code=422,
                detail="Active teacher required",
            )

        return await self.repository.create_halaqa(
            name=name,
            description=description,
            teacher_id=teacher_id,
        )

    async def get_managed_halaqa(self, *, actor, halaqa_id):
        self.parse_id(halaqa_id)

        halaqa = await self.repository.get_halaqa(halaqa_id)

        if halaqa is None:
            raise HTTPException(status_code=404, detail="Halaqa not found")

        if actor.get("role") == "admin":
            return halaqa

        if (
            actor.get("role") == "teacher"
            and halaqa["teacher_id"] == actor["_id"]
        ):
            return halaqa

        raise HTTPException(
            status_code=403,
            detail="Not allowed to manage this Halaqa",
        )

    async def enroll_student(
        self, *, actor, halaqa_id, student_id
    ):
        await self.get_managed_halaqa(
            actor=actor,
            halaqa_id=halaqa_id,
        )

        student = await self.users.get_by_id(
            self.parse_id(student_id)
        )

        if (
            student is None
            or student.get("role") != "student"
            or not student.get("is_active", False)
        ):
            raise HTTPException(
                status_code=422,
                detail="Active student required",
            )

        return await self.repository.enroll_student(
            halaqa_id=halaqa_id,
            student_id=student_id,
        )

    async def list_enrollments(self, *, actor, halaqa_id):
        await self.get_managed_halaqa(
            actor=actor,
            halaqa_id=halaqa_id,
        )

        return await self.repository.list_enrollments(halaqa_id)

    async def list_my_enrollments(self, *, actor):
        if actor.get("role") != "student":
            raise HTTPException(
                status_code=403,
                detail="Student required",
            )

        return await self.repository.list_student_enrollments(
            str(actor["_id"])
        )

    async def create_session(
        self, *, actor, halaqa_id, scheduled_at,
        duration_minutes, notes
    ):
        from datetime import datetime, timezone

        halaqa = await self.get_managed_halaqa(
            actor=actor,
            halaqa_id=halaqa_id,
        )

        if halaqa["status"] != "active":
            raise HTTPException(
                status_code=409,
                detail="Halaqa is not active",
            )

        if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
            raise HTTPException(
                status_code=422,
                detail="Timezone-aware datetime required",
            )

        if scheduled_at.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=422,
                detail="Session must be scheduled in the future",
            )

        return await self.repository.create_session(
            halaqa_id=halaqa_id,
            scheduled_at=scheduled_at.astimezone(timezone.utc),
            duration_minutes=duration_minutes,
            notes=notes,
        )

    async def list_sessions(self, *, actor, halaqa_id):
        await self.get_managed_halaqa(
            actor=actor,
            halaqa_id=halaqa_id,
        )

        return await self.repository.list_sessions(halaqa_id)




    async def list_my_attendance(self, *, actor):
        if actor.get("role") != "student":
            raise HTTPException(
                status_code=403,
                detail="Student required",
            )

        return await self.repository.list_student_attendance(
            str(actor["_id"])
        )

    async def list_session_attendance(self, *, actor, session_id):
        self.parse_id(session_id)

        session = await self.repository.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found",
            )

        await self.get_managed_halaqa(
            actor=actor,
            halaqa_id=str(session["halaqa_id"]),
        )

        return await self.repository.list_session_attendance(
            session_id
        )

    async def record_attendance(
        self, *, actor, session_id, student_id, status, notes
    ):
        from datetime import datetime, timezone

        self.parse_id(session_id)
        self.parse_id(student_id)

        session = await self.repository.get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found",
            )

        halaqa_id = str(session["halaqa_id"])
        halaqa = await self.get_managed_halaqa(
            actor=actor,
            halaqa_id=halaqa_id,
        )

        if halaqa["status"] != "active":
            raise HTTPException(
                status_code=409,
                detail="Halaqa is not active",
            )

        if session["status"] == "cancelled":
            raise HTTPException(
                status_code=409,
                detail="Cancelled session",
            )

        scheduled_at = session["scheduled_at"]
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        if scheduled_at > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=409,
                detail="Session has not started",
            )

        enrollment = await self.repository.get_active_enrollment(
            halaqa_id,
            student_id,
        )

        if enrollment is None:
            raise HTTPException(
                status_code=409,
                detail="Student is not enrolled in this Halaqa",
            )

        return await self.repository.upsert_attendance(
            session_id=session_id,
            student_id=student_id,
            status=status,
            notes=notes,
            recorded_by=str(actor["_id"]),
        )
