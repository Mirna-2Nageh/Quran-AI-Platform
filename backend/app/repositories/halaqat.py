"""MongoDB persistence for Halaqat and enrollments."""

from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError


class HalaqatRepository:
    def __init__(self, database):
        self.halaqat = database["halaqat"]
        self.enrollments = database["halaqa_enrollments"]
        self.sessions = database["halaqa_sessions"]
        self.attendance = database["halaqa_attendance"]
        self.users = database["users"]

    @staticmethod
    def now():
        value = datetime.now(timezone.utc)
        return value.replace(microsecond=(value.microsecond // 1000) * 1000)

    @staticmethod
    def object_id(value):
        if not ObjectId.is_valid(value):
            return None
        return ObjectId(value)

    async def create_halaqa(self, *, name, description, teacher_id):
        teacher = self.object_id(teacher_id)
        if teacher is None:
            return None

        now = self.now()
        document = {
            "name": name,
            "description": description,
            "teacher_id": teacher,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }

        result = await self.halaqat.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_halaqa(self, halaqa_id):
        identifier = self.object_id(halaqa_id)
        if identifier is None:
            return None
        return await self.halaqat.find_one({"_id": identifier})

    async def list_all_halaqat(self, limit=20, offset=0):
        cursor = (
            self.halaqat.find({})
            .sort([("created_at", -1), ("_id", -1)])
            .skip(offset)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def list_teacher_halaqat(self, teacher_id, limit=50):
        identifier = self.object_id(teacher_id)
        if identifier is None:
            return []

        cursor = (
            self.halaqat.find({"teacher_id": identifier})
            .sort([("created_at", -1), ("_id", -1)])
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def enroll_student(self, *, halaqa_id, student_id):
        halaqa = self.object_id(halaqa_id)
        student = self.object_id(student_id)

        if halaqa is None or student is None:
            return None

        now = self.now()

        try:
            await self.enrollments.update_one(
                {"halaqa_id": halaqa, "student_id": student},
                {
                    "$set": {"status": "active"},
                    "$setOnInsert": {
                        "created_at": now,
                    },
                },
                upsert=True,
            )
        except DuplicateKeyError:
            # A concurrent enrollment may have inserted the same pair.
            await self.enrollments.update_one(
                {"halaqa_id": halaqa, "student_id": student},
                {"$set": {"status": "active"}},
            )

        return await self.enrollments.find_one(
            {"halaqa_id": halaqa, "student_id": student}
        )

    async def list_enrollments(self, halaqa_id, limit=100):
        identifier = self.object_id(halaqa_id)
        if identifier is None:
            return []

        cursor = (
            self.enrollments.find(
                {"halaqa_id": identifier, "status": "active"}
            )
            .sort([("created_at", 1), ("_id", 1)])
            .limit(limit)
        )
        documents = await cursor.to_list(length=limit)
        student_ids = list({item["student_id"] for item in documents})

        if student_ids:
            users = await self.users.find(
                {"_id": {"$in": student_ids}},
                {"full_name": 1},
            ).to_list(length=len(student_ids))
            names = {
                user["_id"]: user.get("full_name")
                for user in users
            }
            for item in documents:
                item["student_name"] = names.get(item["student_id"])

        return documents

    async def list_student_enrollments(self, student_id, limit=50):
        identifier = self.object_id(student_id)
        if identifier is None:
            return []

        cursor = (
            self.enrollments.find({
                "student_id": identifier,
                "status": "active",
            })
            .sort([("created_at", -1), ("_id", -1)])
            .limit(limit)
        )
        documents = await cursor.to_list(length=limit)
        halaqa_ids = list({item["halaqa_id"] for item in documents})

        if halaqa_ids:
            halaqat = await self.halaqat.find(
                {"_id": {"$in": halaqa_ids}},
                {"name": 1},
            ).to_list(length=len(halaqa_ids))
            names = {item["_id"]: item["name"] for item in halaqat}
            for item in documents:
                item["halaqa_name"] = names.get(item["halaqa_id"])

        return documents

    async def create_session(
        self, *, halaqa_id, scheduled_at, duration_minutes, notes
    ):
        identifier = self.object_id(halaqa_id)
        if identifier is None:
            return None

        now = self.now()
        document = {
            "halaqa_id": identifier,
            "scheduled_at": scheduled_at,
            "duration_minutes": duration_minutes,
            "notes": notes,
            "status": "scheduled",
            "created_at": now,
            "updated_at": now,
        }
        result = await self.sessions.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def list_sessions(self, halaqa_id, limit=100):
        identifier = self.object_id(halaqa_id)
        if identifier is None:
            return []

        cursor = (
            self.sessions.find({"halaqa_id": identifier})
            .sort([("scheduled_at", 1), ("_id", 1)])
            .limit(limit)
        )
        return await cursor.to_list(length=limit)


    async def get_session(self, session_id):
        identifier = self.object_id(session_id)
        if identifier is None:
            return None
        return await self.sessions.find_one({"_id": identifier})

    async def get_active_enrollment(self, halaqa_id, student_id):
        halaqa = self.object_id(halaqa_id)
        student = self.object_id(student_id)
        if halaqa is None or student is None:
            return None
        return await self.enrollments.find_one({
            "halaqa_id": halaqa,
            "student_id": student,
            "status": "active",
        })

    async def upsert_attendance(
        self, *, session_id, student_id, status, notes, recorded_by
    ):
        session = self.object_id(session_id)
        student = self.object_id(student_id)
        recorder = self.object_id(recorded_by)
        if session is None or student is None or recorder is None:
            return None

        query = {"session_id": session, "student_id": student}
        now = self.now()
        update = {
            "$set": {
                "status": status,
                "notes": notes,
                "recorded_by": recorder,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        }

        try:
            await self.attendance.update_one(query, update, upsert=True)
        except DuplicateKeyError:
            await self.attendance.update_one(query, {
                "$set": update["$set"],
            })

        return await self.attendance.find_one(query)



    async def list_student_attendance(self, student_id):
        identifier = self.object_id(student_id)
        if identifier is None:
            return []

        cursor = self.attendance.find({"student_id": identifier})
        documents = await cursor.sort(
            "created_at", -1
        ).to_list(length=None)

        session_ids = list({item["session_id"] for item in documents})
        if not session_ids:
            return documents

        sessions = await self.sessions.find(
            {"_id": {"$in": session_ids}},
            {"halaqa_id": 1, "scheduled_at": 1},
        ).to_list(length=len(session_ids))

        session_map = {item["_id"]: item for item in sessions}
        halaqa_ids = list({item["halaqa_id"] for item in sessions})

        halaqat = await self.halaqat.find(
            {"_id": {"$in": halaqa_ids}},
            {"name": 1},
        ).to_list(length=len(halaqa_ids)) if halaqa_ids else []

        names = {item["_id"]: item["name"] for item in halaqat}

        for item in documents:
            session = session_map.get(item["session_id"])
            if session:
                item["session_scheduled_at"] = session.get("scheduled_at")
                item["halaqa_name"] = names.get(session["halaqa_id"])

        return documents

    async def list_session_attendance(self, session_id):
        identifier = self.object_id(session_id)
        if identifier is None:
            return []

        cursor = self.attendance.find({"session_id": identifier})
        return await cursor.sort("student_id", 1).to_list(length=None)
