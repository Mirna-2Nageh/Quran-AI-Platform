from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError


class DuplicateEmailError(Exception):
    pass


class UserRepository:
    def __init__(self, database):
        self.collection = database["users"]

    async def get_by_email(self, email: str):
        return await self.collection.find_one({"email": email.lower()})

    async def get_by_id(self, user_id):
        return await self.collection.find_one({"_id": user_id})

    async def list_by_role(
        self, role: str, limit: int = 20, offset: int = 0
    ):
        cursor = (
            self.collection.find(
                {"role": role, "is_active": True},
                {
                    "full_name": 1,
                    "email": 1,
                    "role": 1,
                },
            )
            .sort([("full_name", 1), ("_id", 1)])
            .skip(offset)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def create(
        self,
        email: str,
        full_name: str,
        password_hash: str,
        role: str = "student",
    ):
        if role not in ("student", "teacher"):
            raise ValueError("Unsupported user role")

        now = datetime.now(timezone.utc)

        document = {
            "email": email.lower(),
            "full_name": full_name,
            "password_hash": password_hash,
            "role": role,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        try:
            result = await self.collection.insert_one(document)
        except DuplicateKeyError as exc:
            raise DuplicateEmailError() from exc

        document["_id"] = result.inserted_id
        return document
