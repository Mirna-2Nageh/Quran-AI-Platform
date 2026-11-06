
"""MongoDB persistence for memorization plans and sessions."""

from datetime import datetime, timezone

from bson import ObjectId

from app.repositories.memorization_transactions import run_transaction


class MemorizationRepository:
    @staticmethod
    def _current_timestamp() -> datetime:
        now = datetime.now(timezone.utc)
        return now.replace(microsecond=(now.microsecond // 1000) * 1000)

    def __init__(self, database):
        self.database = database
        self.client = getattr(database, 'client', None)
        self.plans = database["memorization_plans"]
        self.sessions = database["memorization_sessions"]

    async def create_plan(
        self,
        *,
        user_id,
        surah_number: int,
        start_ayah: int,
        end_ayah: int,
    ):
        now = self._current_timestamp()

        document = {
            "user_id": user_id,
            "surah_number": surah_number,
            "start_ayah": start_ayah,
            "end_ayah": end_ayah,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }

        result = await self.plans.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_plan(self, *, user_id, plan_id: str):
        if not ObjectId.is_valid(plan_id):
            return None

        return await self.plans.find_one(
            {
                "_id": ObjectId(plan_id),
                "user_id": user_id,
            }
        )

    async def create_session(
        self,
        *,
        user_id,
        plan_id: str,
        session_type: str,
        result: str,
        notes: str | None = None,
        recitation_session_id: str | None = None,
    ):
        plan = await self.get_plan(
            user_id=user_id,
            plan_id=plan_id,
        )
        if plan is None:
            return None

        if plan.get("status") == "archived":
            raise ValueError("Cannot create sessions for archived plans")

        document = {
            "user_id": user_id,
            "plan_id": plan["_id"],
            "session_type": session_type,
            "result": result,
            "notes": notes,
            "completed_at": self._current_timestamp(),
        }

        if recitation_session_id is not None:
            document["recitation_session_id"] = ObjectId(
                recitation_session_id
            )

        inserted = await self.sessions.insert_one(document)
        document["_id"] = inserted.inserted_id
        return document

    async def list_sessions(
        self,
        *,
        user_id,
        plan_id: str,
        limit: int = 50,
    ):
        plan = await self.get_plan(
            user_id=user_id,
            plan_id=plan_id,
        )
        if plan is None:
            return None

        cursor = (
            self.sessions.find({
                "user_id": user_id,
                "plan_id": plan["_id"],
            })
            .sort([("completed_at", -1), ("_id", -1)])
            .limit(limit)
        )

        return await cursor.to_list(length=limit)

    async def list_plans(self, *, user_id, limit: int = 50):
        cursor = (
            self.plans.find({"user_id": user_id})
            .sort([("created_at", -1), ("_id", -1)])
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def has_sessions(self, *, user_id, plan_id: str) -> bool:
        if not ObjectId.is_valid(plan_id):
            return False
        count = await self.sessions.count_documents(
            {"user_id": user_id, "plan_id": ObjectId(plan_id)},
            limit=1,
        )
        return count > 0

    async def update_plan(
        self,
        *,
        user_id,
        plan_id: str,
        status: str | None = None,
        surah_number: int | None = None,
        start_ayah: int | None = None,
        end_ayah: int | None = None,
    ):
        if not ObjectId.is_valid(plan_id):
            return None

        changes = {
            key: value
            for key, value in {
                "status": status,
                "surah_number": surah_number,
                "start_ayah": start_ayah,
                "end_ayah": end_ayah,
            }.items()
            if value is not None
        }
        if not changes:
            raise ValueError("No update fields provided")

        changes["updated_at"] = self._current_timestamp()

        return await self.plans.find_one_and_update(
            {
                "_id": ObjectId(plan_id),
                "user_id": user_id,
                "status": {"$ne": "archived"},
            },
            {
                "$set": changes
            },
            return_document=True,
        )

    async def list_all_plans_for_progress(self, *, user_id):
        cursor = self.plans.find(
            {"user_id": user_id, "status": {"$ne": "archived"}},
            projection={
                "surah_number": 1,
                "start_ayah": 1,
                "end_ayah": 1,
                "status": 1,
            },
        )
        return await cursor.to_list(length=None)

    async def count_revision_sessions(self, *, user_id):
        return await self.sessions.count_documents({
            "user_id": user_id,
            "session_type": "revision",
        })

    async def create_session_atomic(
        self,
        *,
        user_id,
        plan_id: str,
        session_type: str,
        result: str,
        notes: str | None = None,
        recitation_session_id: str | None = None,
    ):
        """Create a session while protecting the parent plan."""
        if not ObjectId.is_valid(plan_id):
            return None
        if self.client is None:
            raise RuntimeError("MongoDB client required for atomic session creation")

        async def operation(session):
            plan = await self.plans.find_one_and_update(
                {
                    "_id": ObjectId(plan_id),
                    "user_id": user_id,
                    "status": {"$ne": "archived"},
                },
                {"$inc": {"revision": 1}},
                return_document=True,
                session=session,
            )
            if plan is None:
                existing = await self.plans.find_one(
                    {"_id": ObjectId(plan_id), "user_id": user_id},
                    session=session,
                )
                if existing and existing.get("status") == "archived":
                    raise ValueError("Cannot create sessions for archived plans")
                return None

            document = {
                "user_id": user_id,
                "plan_id": plan["_id"],
                "session_type": session_type,
                "result": result,
                "notes": notes,
                "completed_at": self._current_timestamp(),
            }
            if recitation_session_id is not None:
                document["recitation_session_id"] = ObjectId(
                    recitation_session_id
                )

            inserted = await self.sessions.insert_one(
                document, session=session
            )
            document["_id"] = inserted.inserted_id
            return document

        return await run_transaction(self.client, operation)

    async def update_plan_atomic(
        self,
        *,
        user_id,
        plan_id: str,
        status: str | None = None,
        surah_number: int | None = None,
        start_ayah: int | None = None,
        end_ayah: int | None = None,
    ):
        """Update a plan atomically with session/range checks."""
        from app.services.quran_text import validate_quran_range

        if not ObjectId.is_valid(plan_id):
            return None
        if self.client is None:
            raise RuntimeError("MongoDB client required for atomic plan updates")

        changes = {
            key: value
            for key, value in {
                "status": status,
                "surah_number": surah_number,
                "start_ayah": start_ayah,
                "end_ayah": end_ayah,
            }.items()
            if value is not None
        }
        if not changes:
            raise ValueError("No update fields provided")

        async def operation(session):
            query = {"_id": ObjectId(plan_id), "user_id": user_id}
            plan = await self.plans.find_one(query, session=session)

            if plan is None:
                return None
            if plan.get("status") == "archived":
                raise ValueError("Archived plan cannot be edited")

            if {"surah_number", "start_ayah", "end_ayah"} & changes.keys():
                count = await self.sessions.count_documents(
                    {"user_id": user_id, "plan_id": ObjectId(plan_id)},
                    limit=1,
                    session=session,
                )
                if count:
                    raise ValueError("Cannot edit range after sessions exist")

                validate_quran_range(
                    changes.get("surah_number", plan["surah_number"]),
                    changes.get("start_ayah", plan["start_ayah"]),
                    changes.get("end_ayah", plan["end_ayah"]),
                )

            return await self.plans.find_one_and_update(
                {**query, "status": {"$ne": "archived"}},
                {
                    "$set": {
                        **changes,
                        "updated_at": self._current_timestamp(),
                    },
                    "$inc": {"revision": 1},
                },
                return_document=True,
                session=session,
            )

        return await run_transaction(self.client, operation)
