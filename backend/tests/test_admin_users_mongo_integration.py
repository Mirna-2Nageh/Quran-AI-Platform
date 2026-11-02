"""Real MongoDB integration test for admin user directory."""

import asyncio
import os
from uuid import uuid4

import pytest
from app.repositories.users import UserRepository
from pymongo import AsyncMongoClient


def test_admin_user_directory_real_mongodb():
    uri = os.environ.get("QURAN_AI_TEST_MONGO_URI", "")
    if not uri:
        pytest.skip("MongoDB test URI is not configured")

    if os.environ.get("QURAN_AI_ENVIRONMENT") != "testing":
        pytest.fail("Testing environment required")

    if os.environ.get("QURAN_AI_MONGO_DB_NAME") != "quran_ai_ci_test":
        pytest.fail("Refusing non-test database")

    async def run():
        client = AsyncMongoClient(
            uri, serverSelectionTimeoutMS=5000
        )
        database = client["quran_ai_ci_test"]
        collection = database["users"]
        marker = f"admin-directory-test-{uuid4().hex}"

        documents = [
            {
                "email": f"{marker}-a@example.com",
                "full_name": f"{marker} Alice",
                "role": "teacher",
                "is_active": True,
                "password_hash": "secret",
            },
            {
                "email": f"{marker}-b@example.com",
                "full_name": f"{marker} Bob",
                "role": "teacher",
                "is_active": True,
                "password_hash": "secret",
            },
            {
                "email": f"{marker}-c@example.com",
                "full_name": f"{marker} Charlie",
                "role": "teacher",
                "is_active": False,
                "password_hash": "secret",
            },
            {
                "email": f"{marker}-d@example.com",
                "full_name": f"{marker} Student",
                "role": "student",
                "is_active": True,
                "password_hash": "secret",
            },
        ]

        try:
            await client.admin.command("ping")
            result = await collection.insert_many(documents)
            inserted_ids = set(result.inserted_ids)

            repository = UserRepository(database)

            teachers = await repository.list_by_role(
                "teacher", limit=100, offset=0
            )
            own_teachers = [
                user for user in teachers
                if user["_id"] in inserted_ids
            ]

            assert len(own_teachers) == 2
            assert [u["full_name"] for u in own_teachers] == [
                f"{marker} Alice",
                f"{marker} Bob",
            ]
            assert all("password_hash" not in u for u in own_teachers)

            students = await repository.list_by_role(
                "student", limit=100, offset=0
            )
            assert any(
                user["_id"] in inserted_ids
                for user in students
            )

            assert all(
                user["role"] == "teacher"
                for user in teachers
            )

        finally:
            await collection.delete_many(
                {"email": {"$regex": f"^{marker}"}}
            )
            await client.close()

    asyncio.run(run())
