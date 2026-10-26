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

        user = await database["users"].find_one({"email": email})

        if user:
            await database["sessions"].delete_many({"user_id": user["_id"]})

            await database["users"].delete_one({"_id": user["_id"], "email": email})

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

            assert client.cookies.get("quran_session"), "Session cookie missing"

            me = client.get("/api/v1/auth/me")
            check(me, 200, "Authenticated /me")

            assert me.json()["email"] == email
            assert me.json()["role"] == "student"

            missing_csrf = client.post("/api/v1/auth/logout")
            check(missing_csrf, 403, "Missing CSRF token")

            csrf_token = login.headers.get("X-CSRF-Token")
            assert csrf_token, "CSRF token missing from login"

            # Recover a new CSRF token using the existing session.
            refresh = client.get("/api/v1/auth/csrf")
            check(refresh, 200, "CSRF recovery")

            new_csrf_token = refresh.headers.get("X-CSRF-Token")
            assert new_csrf_token, "Recovered CSRF token missing"
            assert new_csrf_token != csrf_token, "CSRF token was not rotated"
            assert refresh.headers.get("cache-control") == "no-store"

            # The old token must no longer authorize logout.
            stale_logout = client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": csrf_token},
            )
            check(stale_logout, 403, "Old CSRF token rejected")

            # Failed logout must not invalidate the session.
            still_authenticated = client.get("/api/v1/auth/me")
            check(still_authenticated, 200, "Session preserved")

            # The recovered token must authorize logout.
            logout = client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": new_csrf_token},
            )
            check(logout, 200, "Logout with recovered CSRF")

            after_logout = client.get("/api/v1/auth/me")
            check(after_logout, 401, "Session invalidation")

            # CSRF recovery must reject requests without a session.
            unauthenticated_csrf = client.get("/api/v1/auth/csrf")
            check(unauthenticated_csrf, 401, "CSRF without session")

            # Test login throttling with a separate nonexistent account.
            blocked_email = f"blocked-{secrets.token_hex(8)}@example.com"

            try:
                for attempt in range(5):
                    failed = client.post(
                        "/api/v1/auth/login",
                        json={
                            "email": blocked_email,
                            "password": "WrongPassword123!",
                        },
                    )
                    check(failed, 401, f"Failed attempt {attempt + 1}")

                blocked = client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": blocked_email,
                        "password": "WrongPassword123!",
                    },
                )
                check(blocked, 429, "Rate limit enforcement")
                assert blocked.headers.get("retry-after") == "900"
            finally:
                from app.security.rate_limit import LoginRateLimiter

                async def clear_test_limit():
                    mongo = AsyncMongoClient(settings.mongo_uri)
                    try:
                        limiter = LoginRateLimiter(mongo[settings.mongo_db_name])
                        await limiter.clear(blocked_email)
                    finally:
                        await mongo.close()

                asyncio.run(clear_test_limit())

            print("\nAUTHENTICATION INTEGRATION: PASSED")

    finally:
        asyncio.run(cleanup())


if __name__ == "__main__":
    main()
