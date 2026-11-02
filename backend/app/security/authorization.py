"""Reusable authentication and role authorization dependencies."""

from fastapi import Depends, HTTPException, Request

from app.api.v1.auth import (
    COOKIE_NAME,
    check_origin,
    get_auth_service,
)
from app.services.auth import AuthService


async def current_user(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    token = request.cookies.get(COOKIE_NAME)
    user = await service.get_current_user(token)

    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user


async def current_user_write(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    check_origin(request)

    token = request.cookies.get(COOKIE_NAME)
    user = await service.get_current_user(token)

    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    csrf_token = request.headers.get("X-CSRF-Token")

    if not await service.verify_csrf(token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    return user


def require_roles(*allowed_roles: str):
    async def dependency(user=Depends(current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


def require_roles_write(*allowed_roles: str):
    async def dependency(user=Depends(current_user_write)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency
