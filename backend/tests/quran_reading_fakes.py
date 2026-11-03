"""In-memory Quran reading repository for HTTP tests."""

from datetime import datetime, timezone


class FakeQuranReadingRepository:
    bookmarks = {}
    progress = {}

    def __init__(self, database):
        self.database = database

    @classmethod
    def reset(cls):
        cls.bookmarks = {}
        cls.progress = {}

    async def list_bookmarks(self, user_id):
        return [
            value for key, value in self.bookmarks.items()
            if key[0] == user_id
        ]

    async def add_bookmark(self, user_id, surah_number, ayah_number):
        key = (user_id, surah_number, ayah_number)
        if key not in self.bookmarks:
            self.bookmarks[key] = {
                "surah_number": surah_number,
                "ayah_number": ayah_number,
                "created_at": datetime.now(timezone.utc),
            }
        return self.bookmarks[key]

    async def remove_bookmark(self, user_id, surah_number, ayah_number):
        key = (user_id, surah_number, ayah_number)
        return self.bookmarks.pop(key, None) is not None

    async def get_progress(self, user_id):
        return self.progress.get(user_id)

    async def save_progress(self, user_id, surah_number, ayah_number):
        self.progress[user_id] = {
            "surah_number": surah_number,
            "ayah_number": ayah_number,
            "updated_at": datetime.now(timezone.utc),
        }
        return self.progress[user_id]
