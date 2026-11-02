"""Admin-only user directory."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr

from app.repositories.users import DuplicateEmailError, UserRepository
from app.security.authorization import require_roles, require_roles_write
from app.security.passwords import hash_password

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


class AdminUserResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: Literal["teacher", "student"]


@router.get("", response_model=list[AdminUserResponse])
async def list_admin_users(
    request: Request,
    role: Literal["teacher", "student"],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    actor=Depends(require_roles("admin")),
):
    repository = UserRepository(request.app.state.database)
    users = await repository.list_by_role(
        role=role,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": str(user["_id"]),
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        }
        for user in users
    ]


class CreateTeacherRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str


@router.post("", response_model=AdminUserResponse, status_code=201)
async def create_teacher(
    payload: CreateTeacherRequest,
    request: Request,
    actor=Depends(require_roles_write("admin")),
):
    full_name = payload.full_name.strip()

    if not 2 <= len(full_name) <= 100:
        raise HTTPException(status_code=422, detail="Invalid full name")

    if not 12 <= len(payload.password) <= 128:
        raise HTTPException(
            status_code=422,
            detail="Password must be 12-128 characters",
        )

    repository = UserRepository(request.app.state.database)

    try:
        user = await repository.create(
            email=str(payload.email).strip().lower(),
            full_name=full_name,
            password_hash=hash_password(payload.password),
            role="teacher",
        )
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        ) from exc

    return {
        "id": str(user["_id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "role": "teacher",
    }
