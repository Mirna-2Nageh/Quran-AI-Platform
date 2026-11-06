"""MongoDB persistence for recitation analysis sessions."""

from datetime import datetime, timezone

from bson import ObjectId


class RecitationSessionRepository:
    @staticmethod
    def _current_timestamp() -> datetime:
        now = datetime.now(timezone.utc)
        return now.replace(microsecond=(now.microsecond // 1000) * 1000)

    def __init__(self, database):
        self.collection = database["recitation_sessions"]

    async def create(
        self,
        *,
        user_id,
        surah_number: int,
        ayah_number: int,
        end_ayah_number: int,
        expected_text: str,
        recognized_text: str,
        alignment: dict,
    ):
        document = {
            "user_id": user_id,
            "surah_number": surah_number,
            "ayah_number": ayah_number,
            "end_ayah_number": end_ayah_number,
            "expected_text": expected_text,
            "recognized_text": recognized_text,
            "alignment": alignment,
            "analysis_type": "word_level_asr_alignment",
            "tajweed_analyzed": False,
            "created_at": self._current_timestamp(),
        }

        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id

        return document

    async def get_by_id_for_user(self, *, user_id, session_id: str):
        """Retrieve a recitation session owned by the user."""
        if not ObjectId.is_valid(session_id):
            return None

        return await self.collection.find_one({
            "_id": ObjectId(session_id),
            "user_id": user_id,
        })

    async def list_by_user(self, user_id, limit: int = 20):
        cursor = (
            self.collection.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)


    async def list_page_by_user(
        self,
        *,
        user_id,
        limit: int = 20,
        after: tuple | None = None,
    ):
        """Return a stable page and whether older sessions exist."""
        query = {"user_id": user_id}

        if after is not None:
            created_at, object_id = after
            query["$or"] = [
                {"created_at": {"$lt": created_at}},
                {
                    "created_at": created_at,
                    "_id": {"$lt": object_id},
                },
            ]

        cursor = (
            self.collection.find(query)
            .sort([("created_at", -1), ("_id", -1)])
            .limit(limit + 1)
        )

        documents = await cursor.to_list(length=limit + 1)

        return documents[:limit], len(documents) > limit
