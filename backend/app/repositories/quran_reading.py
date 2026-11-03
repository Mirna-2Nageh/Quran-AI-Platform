"""MongoDB persistence for Quran bookmarks and reading progress."""

from datetime import datetime, timezone


class QuranReadingRepository:
    def __init__(self, database):
        self.bookmarks = database["quran_bookmarks"]
        self.progress = database["quran_reading_progress"]

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    async def list_bookmarks(self, user_id):
        cursor = self.bookmarks.find({"user_id": user_id}).sort(
            [("surah_number", 1), ("ayah_number", 1)]
        )
        return await cursor.to_list(length=None)

    async def add_bookmark(self, user_id, surah_number, ayah_number):
        key = {
            "user_id": user_id,
            "surah_number": surah_number,
            "ayah_number": ayah_number,
        }
        await self.bookmarks.update_one(
            key,
            {"$setOnInsert": {**key, "created_at": self.now()}},
            upsert=True,
        )
        return await self.bookmarks.find_one(key)

    async def remove_bookmark(self, user_id, surah_number, ayah_number):
        result = await self.bookmarks.delete_one({
            "user_id": user_id,
            "surah_number": surah_number,
            "ayah_number": ayah_number,
        })
        return result.deleted_count > 0

    async def get_progress(self, user_id):
        return await self.progress.find_one({"user_id": user_id})

    async def save_progress(self, user_id, surah_number, ayah_number):
        await self.progress.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "surah_number": surah_number,
                    "ayah_number": ayah_number,
                    "updated_at": self.now(),
                }
            },
            upsert=True,
        )
        return await self.get_progress(user_id)
