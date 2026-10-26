from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.repositories.users import DuplicateEmailError
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.auth import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["Authentication"])

COOKIE_NAME = "quran_session"


def get_auth_service(request: Request) -> AuthService:
    database = getattr(request.app.state, "database", None)

    if database is None:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    return AuthService(database)


def user_response(user) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        created_at=user["created_at"],
    )


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")

    if not origin:
        return

    settings = get_settings()
    allowed = (
        {"http://localhost:5173", "http://127.0.0.1:5173"}
        if settings.environment != "production"
        else set()
    )

    if origin not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Origin not allowed",
        )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    check_origin(request)

    try:
        user = await service.register(
            payload.email,
            payload.full_name,
            payload.password,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        ) from exc

    return user_response(user)


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
):
    check_origin(request)

    try:
        user, token = await service.login(
            payload.email,
            payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        ) from exc

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=get_settings().environment == "production",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )

    return user_response(user)


@router.get("/me", response_model=UserResponse)
async def me(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    token = request.cookies.get(COOKIE_NAME)
    user = await service.get_current_user(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    return user_response(user)


@router.post("/logout")
async def logout(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    check_origin(request)

    token = request.cookies.get(COOKIE_NAME)
    await service.logout(token)

    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie(COOKIE_NAME, path="/")

    return response
