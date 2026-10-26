import hashlib
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


class LoginRateLimiter:
    MAX_ATTEMPTS = 5
    WINDOW = timedelta(minutes=15)

    def __init__(self, database):
        self.collection = database["login_attempts"]

    @staticmethod
    def _key(email: str) -> str:
        normalized = email.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def is_blocked(self, email: str) -> bool:
        now = datetime.now(timezone.utc)

        record = await self.collection.find_one(
            {
                "_id": self._key(email),
                "expires_at": {"$gt": now},
            }
        )

        return record is not None and record.get("attempts", 0) >= self.MAX_ATTEMPTS

    async def record_failure(self, email: str) -> None:
        key = self._key(email)
        now = datetime.now(timezone.utc)
        expires_at = now + self.WINDOW

        # A single document update increments the counter or
        # resets it when its previous window has expired.
        expired = {
            "$lte": [
                {"$ifNull": ["$expires_at", now]},
                now,
            ]
        }

        pipeline = [
            {
                "$set": {
                    "attempts": {
                        "$cond": [
                            expired,
                            1,
                            {"$add": [{"$ifNull": ["$attempts", 0]}, 1]},
                        ]
                    },
                    "expires_at": {
                        "$cond": [
                            expired,
                            expires_at,
                            "$expires_at",
                        ]
                    },
                }
            }
        ]

        # Concurrent first attempts can race to insert the same
        # _id. Retry against the document created by the winner.
        for attempt in range(2):
            try:
                await self.collection.find_one_and_update(
                    {"_id": key},
                    pipeline,
                    upsert=True,
                    return_document=ReturnDocument.AFTER,
                )
                return
            except DuplicateKeyError:
                if attempt == 1:
                    raise

    async def clear(self, email: str) -> None:
        await self.collection.delete_one({"_id": self._key(email)})
