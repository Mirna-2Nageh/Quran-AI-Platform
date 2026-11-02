"""Real MongoDB integration test for teacher account creation."""

import asyncio
import os
from uuid import uuid4

import pytest
from app.repositories.users import DuplicateEmailError, UserRepository
from app.security.passwords import hash_password, verify_password
from pymongo import AsyncMongoClient


def test_teacher_creation_real_mongodb():
    uri = os.environ.get("QURAN_AI_TEST_MONGO_URI", "")

    if not uri:
        pytest.skip("MongoDB test URI is not configured")

    if os.environ.get("QURAN_AI_ENVIRONMENT") != "testing":
        pytest.fail("Testing environment required")

    if os.environ.get("QURAN_AI_MONGO_DB_NAME") != "quran_ai_ci_test":
        pytest.fail("Refusing non-test database")

    async def run():
        client = AsyncMongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
        )
        database = client["quran_ai_ci_test"]
        repository = UserRepository(database)

        email = f"teacher-test-{uuid4().hex}@example.com"
        password = "StrongTeacherPassword123!"
        password_hash = hash_password(password)

        try:
            await client.admin.command("ping")
            await database["users"].create_index(
                "email",
                unique=True,
            )

            user = await repository.create(
                email=email,
                full_name="Integration Test Teacher",
                password_hash=password_hash,
                role="teacher",
            )

            assert user["role"] == "teacher"
            assert user["is_active"] is True

            stored = await repository.get_by_email(email)

            assert stored is not None
            assert stored["role"] == "teacher"
            assert stored["password_hash"] != password
            assert verify_password(
                password,
                stored["password_hash"],
            )

            with pytest.raises(DuplicateEmailError):
                await repository.create(
                    email=email,
                    full_name="Duplicate Teacher",
                    password_hash=password_hash,
                    role="teacher",
                )

        finally:
            await database["users"].delete_many(
                {"email": email}
            )
            await client.close()

    asyncio.run(run())
