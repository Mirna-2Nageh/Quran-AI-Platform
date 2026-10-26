"""MongoDB persistence for recitation analysis sessions."""

from datetime import datetime, timezone


class RecitationSessionRepository:
    def __init__(self, database):
        self.collection = database["recitation_sessions"]

    async def create(
        self,
        *,
        user_id,
        surah_number: int,
        ayah_number: int,
        expected_text: str,
        recognized_text: str,
        alignment: dict,
    ):
        document = {
            "user_id": user_id,
            "surah_number": surah_number,
            "ayah_number": ayah_number,
            "expected_text": expected_text,
            "recognized_text": recognized_text,
            "alignment": alignment,
            "analysis_type": "word_level_asr_alignment",
            "tajweed_analyzed": False,
            "created_at": datetime.now(timezone.utc),
        }

        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id

        return document

    async def list_by_user(self, user_id, limit: int = 20):
        cursor = (
            self.collection.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)
