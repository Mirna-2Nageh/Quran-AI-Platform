
"""MongoDB persistence for memorization plans and sessions."""

from datetime import datetime, timezone

from bson import ObjectId


class MemorizationRepository:
    @staticmethod
    def _current_timestamp() -> datetime:
        now = datetime.now(timezone.utc)
        return now.replace(microsecond=(now.microsecond // 1000) * 1000)

    def __init__(self, database):
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
    ):
        plan = await self.get_plan(
            user_id=user_id,
            plan_id=plan_id,
        )
        if plan is None:
            return None

        document = {
            "user_id": user_id,
            "plan_id": plan["_id"],
            "session_type": session_type,
            "result": result,
            "notes": notes,
            "completed_at": self._current_timestamp(),
        }

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

    async def update_plan(
        self,
        *,
        user_id,
        plan_id: str,
        status: str,
    ):
        if not ObjectId.is_valid(plan_id):
            return None

        return await self.plans.find_one_and_update(
            {
                "_id": ObjectId(plan_id),
                "user_id": user_id,
            },
            {
                "$set": {
                    "status": status,
                    "updated_at": self._current_timestamp(),
                }
            },
            return_document=True,
        )

    async def list_all_plans_for_progress(self, *, user_id):
        cursor = self.plans.find(
            {"user_id": user_id},
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
