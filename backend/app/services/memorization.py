"""Business logic for Quran memorization tracking."""

from app.services.memorization_progress import calculate_progress
from app.services.quran_text import validate_quran_range


class MemorizationService:
    def __init__(self, repository):
        self.repository = repository

    async def create_plan(
        self,
        *,
        user_id,
        surah_number: int,
        start_ayah: int,
        end_ayah: int,
    ):
        validate_quran_range(
            surah_number,
            start_ayah,
            end_ayah,
        )

        return await self.repository.create_plan(
            user_id=user_id,
            surah_number=surah_number,
            start_ayah=start_ayah,
            end_ayah=end_ayah,
        )

    async def get_plan(self, *, user_id, plan_id: str):
        return await self.repository.get_plan(
            user_id=user_id,
            plan_id=plan_id,
        )

    async def list_plans(self, *, user_id, limit: int = 50):
        return await self.repository.list_plans(
            user_id=user_id,
            limit=limit,
        )

    async def update_plan(self, *, user_id, plan_id: str, status: str):
        return await self.repository.update_plan(
            user_id=user_id,
            plan_id=plan_id,
            status=status,
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
        return await self.repository.create_session(
            user_id=user_id,
            plan_id=plan_id,
            session_type=session_type,
            result=result,
            notes=notes,
        )

    async def list_sessions(
        self, *, user_id, plan_id: str, limit: int = 50
    ):
        return await self.repository.list_sessions(
            user_id=user_id,
            plan_id=plan_id,
            limit=limit,
        )

    async def get_progress(self, *, user_id):
        plans = await self.repository.list_all_plans_for_progress(
            user_id=user_id,
        )
        revision_count = await self.repository.count_revision_sessions(
            user_id=user_id,
        )
        progress = calculate_progress(plans)
        progress["revision_sessions"] = revision_count
        return progress
