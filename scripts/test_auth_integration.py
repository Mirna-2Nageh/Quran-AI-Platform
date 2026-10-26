import asyncio
import secrets

from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient

from app.config import get_settings
from app.main import app

settings = get_settings()
email = f"auth-test-{secrets.token_hex(8)}@example.com"
password = "IntegrationTestPassword123!"
user_id = None


def check(response, expected_status, label):
    print(f"{label}: HTTP {response.status_code}")

    if response.status_code != expected_status:
        raise AssertionError(
            f"{label}: expected {expected_status}, "
            f"got {response.status_code}: {response.text}"
        )


async def cleanup():
    if not settings.mongo_uri:
        return

    client = AsyncMongoClient(settings.mongo_uri)

    try:
        database = client[settings.mongo_db_name]

        user = await database["users"].find_one(
            {"email": email}
        )

        if user:
            await database["sessions"].delete_many(
                {"user_id": user["_id"]}
            )

            await database["users"].delete_one(
                {"_id": user["_id"], "email": email}
            )

            print("Cleanup: test user and sessions removed")
    finally:
        await client.close()


def main():
    if not settings.mongo_uri:
        raise RuntimeError("MongoDB is not configured")

    try:
        with TestClient(app) as client:
            register = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "full_name": "Integration Test User",
                    "password": password,
                },
            )
            check(register, 201, "Register")

            duplicate = client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "full_name": "Integration Test User",
                    "password": password,
                },
            )
            check(duplicate, 409, "Duplicate email")

            wrong_login = client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": "IncorrectPassword123!",
                },
            )
            check(wrong_login, 401, "Invalid login")

            login = client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                },
            )
            check(login, 200, "Login")

            assert client.cookies.get("quran_session"), (
                "Session cookie missing"
            )

            me = client.get("/api/v1/auth/me")
            check(me, 200, "Authenticated /me")

            assert me.json()["email"] == email
            assert me.json()["role"] == "student"

            logout = client.post("/api/v1/auth/logout")
            check(logout, 200, "Logout")

            after_logout = client.get("/api/v1/auth/me")
            check(after_logout, 401, "Session invalidation")

            print("\nAUTHENTICATION INTEGRATION: PASSED")

    finally:
        asyncio.run(cleanup())


if __name__ == "__main__":
    main()
