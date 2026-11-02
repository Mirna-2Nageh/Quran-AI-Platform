"""Tests for reusable Halaqat authorization dependencies."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.security.authorization import (
    current_user,
    current_user_write,
    require_roles,
    require_roles_write,
)
from fastapi import HTTPException
from starlette.requests import Request


def make_request(cookie=None, csrf=None):
    headers = []
    if cookie:
        headers.append((b"cookie", f"quran_session={cookie}".encode()))
    if csrf:
        headers.append((b"x-csrf-token", csrf.encode()))

    return Request({"type": "http", "headers": headers})


@pytest.mark.asyncio
async def test_current_user_requires_login():
    service = MagicMock()
    service.get_current_user = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await current_user(make_request(), service)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_current_user_accepts_valid_session():
    service = MagicMock()
    service.get_current_user = AsyncMock(
        return_value={"role": "student"}
    )

    user = await current_user(make_request(cookie="session"), service)

    assert user["role"] == "student"


@pytest.mark.asyncio
async def test_write_rejects_invalid_csrf():
    service = MagicMock()
    service.get_current_user = AsyncMock(
        return_value={"role": "teacher"}
    )
    service.verify_csrf = AsyncMock(return_value=False)

    with pytest.raises(HTTPException) as exc:
        await current_user_write(
            make_request(cookie="session", csrf="invalid"),
            service,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_write_accepts_valid_csrf():
    service = MagicMock()
    service.get_current_user = AsyncMock(
        return_value={"role": "teacher"}
    )
    service.verify_csrf = AsyncMock(return_value=True)

    user = await current_user_write(
        make_request(cookie="session", csrf="valid"),
        service,
    )

    assert user["role"] == "teacher"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        ("admin", True),
        ("teacher", True),
        ("student", False),
    ],
)
async def test_read_role_permissions(role, allowed):
    dependency = require_roles("admin", "teacher")
    user = {"role": role}

    if allowed:
        assert await dependency(user) == user
    else:
        with pytest.raises(HTTPException) as exc:
            await dependency(user)
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_write_role_permissions():
    dependency = require_roles_write("admin")

    assert await dependency({"role": "admin"}) == {"role": "admin"}

    with pytest.raises(HTTPException) as exc:
        await dependency({"role": "teacher"})

    assert exc.value.status_code == 403
