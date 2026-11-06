"""Real HTTP authentication flow using isolated MongoDB."""

import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.api.v1.auth import get_auth_service
from app.main import app
from app.services.auth import AuthService


@pytest.mark.asyncio
async def test_real_authentication_flow():
    uri = os.environ["QURAN_AI_TEST_MONGO_URI"]
    mongo = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
    db = mongo["quran_ai_ci_test"]
    email = f"auth-{uuid4().hex}@example.com"
    password = "SecureTestPassword2026!"

    def test_auth_service():
        return AuthService(db)

    previous = app.dependency_overrides.get(get_auth_service)
    app.dependency_overrides[get_auth_service] = test_auth_service

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            register = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "full_name": "Integration Test User",
                    "password": password,
                },
            )
            assert register.status_code == 201, register.text

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200, login.text
            assert "quran_session" in client.cookies

            me = await client.get("/api/v1/auth/me")
            assert me.status_code == 200, me.text
            assert me.json()["email"] == email

            csrf = await client.get("/api/v1/auth/csrf")
            assert csrf.status_code == 200, csrf.text
            token = csrf.headers["X-CSRF-Token"]

            logout = await client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": token},
            )
            assert logout.status_code == 200, logout.text

            after = await client.get("/api/v1/auth/me")
            assert after.status_code == 401, after.text
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_auth_service, None)
        else:
            app.dependency_overrides[get_auth_service] = previous

        user = await db["users"].find_one({"email": email})
        if user:
            await db["sessions"].delete_many({"user_id": user["_id"]})
            await db["users"].delete_one({"_id": user["_id"]})
        await mongo.close()


@pytest.mark.asyncio
async def test_csrf_refresh_preserves_token_across_tabs():
    from app.security.sessions import hash_session_token

    uri = os.environ["QURAN_AI_TEST_MONGO_URI"]
    mongo = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
    db = mongo["quran_ai_ci_test"]
    service = AuthService(db)

    session_token = uuid4().hex
    session_hash = hash_session_token(session_token)

    try:
        from datetime import datetime, timedelta, timezone

        await db["sessions"].insert_one({
            "token_hash": session_hash,
            "csrf_version": 2,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        })

        first = await service.refresh_csrf(session_token)
        second = await service.refresh_csrf(session_token)

        assert first == second
        assert await service.verify_csrf(session_token, second)
        assert await service.verify_csrf(session_token, first)
    finally:
        await db["sessions"].delete_one({"token_hash": session_hash})
        await mongo.close()




@pytest.mark.asyncio
async def test_csrf_session_security():
    from datetime import datetime, timedelta, timezone
    from app.security.sessions import hash_session_token

    mongo = AsyncMongoClient(os.environ["QURAN_AI_TEST_MONGO_URI"])
    db = mongo["quran_ai_ci_test"]
    service = AuthService(db)

    a, b, expired, legacy = [uuid4().hex for _ in range(4)]
    tokens = [a, b, expired, legacy]
    now = datetime.now(timezone.utc)

    try:
        for token in tokens:
            await db["sessions"].insert_one({
                "token_hash": hash_session_token(token),
                "csrf_version": 2 if token != legacy else 1,
                "expires_at": now + timedelta(hours=1)
                if token != expired else now - timedelta(hours=1),
                **({"csrf_hash": hash_session_token("legacy-secret")}
                   if token == legacy else {}),
            })

        csrf_a = await service.refresh_csrf(a)
        assert csrf_a
        assert await service.verify_csrf(a, csrf_a)
        assert not await service.verify_csrf(b, csrf_a)
        assert await service.refresh_csrf(expired) is None
        assert not await service.verify_csrf(expired, csrf_a)

        assert await service.verify_csrf(legacy, "legacy-secret")
        assert await service.refresh_csrf(legacy)
        assert await service.verify_csrf(legacy, "legacy-secret")

        await service.logout(a)
        assert not await service.verify_csrf(a, csrf_a)
        assert await service.refresh_csrf(a) is None
    finally:
        await db["sessions"].delete_many({
            "token_hash": {"$in": [hash_session_token(t) for t in tokens]}
        })
        await mongo.close()
