"""Authenticated Quran memorization endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.auth import (
    COOKIE_NAME,
    check_origin,
    get_auth_service,
)
from app.repositories.memorization import MemorizationRepository
from app.schemas.memorization import (
    MemorizationPlanCreate,
    MemorizationPlanResponse,
    MemorizationPlanUpdate,
    MemorizationProgressResponse,
    MemorizationSessionCreate,
    MemorizationSessionResponse,
)
from app.services.auth import AuthService
from app.services.memorization import MemorizationService
from app.services.quran_text import QuranTextError

router = APIRouter(prefix="/memorization", tags=["Memorization"])


async def get_current_memorization_user(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    token = request.cookies.get(COOKIE_NAME)
    user = await service.get_current_user(token)

    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user


async def verify_memorization_write(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    check_origin(request)

    token = request.cookies.get(COOKIE_NAME)
    csrf_token = request.headers.get("X-CSRF-Token")

    user = await service.get_current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not await service.verify_csrf(token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    return user



@router.get("/progress", response_model=MemorizationProgressResponse)
async def get_memorization_progress(
    request: Request,
    user=Depends(get_current_memorization_user),
):
    service = MemorizationService(
        MemorizationRepository(request.app.state.database)
    )
    return await service.get_progress(user_id=user["_id"])


@router.post("/plans", response_model=MemorizationPlanResponse, status_code=201)
async def create_memorization_plan(
    payload: MemorizationPlanCreate,
    request: Request,
    user=Depends(verify_memorization_write),
):
    service = MemorizationService(
        MemorizationRepository(request.app.state.database)
    )

    try:
        plan = await service.create_plan(
            user_id=user["_id"],
            surah_number=payload.surah_number,
            start_ayah=payload.start_ayah,
            end_ayah=payload.end_ayah,
        )
    except QuranTextError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "id": str(plan["_id"]),
        "surah_number": plan["surah_number"],
        "start_ayah": plan["start_ayah"],
        "end_ayah": plan["end_ayah"],
        "status": plan["status"],
        "created_at": plan["created_at"],
        "updated_at": plan["updated_at"],
    }


@router.get("/plans", response_model=list[MemorizationPlanResponse])
async def list_memorization_plans(
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
    user=Depends(get_current_memorization_user),
):
    service = MemorizationService(
        MemorizationRepository(request.app.state.database)
    )
    plans = await service.list_plans(
        user_id=user["_id"],
        limit=limit,
    )
    return [
        {
            "id": str(plan["_id"]),
            "surah_number": plan["surah_number"],
            "start_ayah": plan["start_ayah"],
            "end_ayah": plan["end_ayah"],
            "status": plan["status"],
            "created_at": plan["created_at"],
            "updated_at": plan["updated_at"],
        }
        for plan in plans
    ]


@router.get("/plans/{plan_id}", response_model=MemorizationPlanResponse)
async def get_memorization_plan(
    plan_id: str,
    request: Request,
    user=Depends(get_current_memorization_user),
):
    service = MemorizationService(
        MemorizationRepository(request.app.state.database)
    )
    plan = await service.get_plan(
        user_id=user["_id"],
        plan_id=plan_id,
    )

    if plan is None:
        raise HTTPException(
            status_code=404,
            detail="Memorization plan not found",
        )

    return {
        "id": str(plan["_id"]),
        "surah_number": plan["surah_number"],
        "start_ayah": plan["start_ayah"],
        "end_ayah": plan["end_ayah"],
        "status": plan["status"],
        "created_at": plan["created_at"],
        "updated_at": plan["updated_at"],
    }


@router.patch("/plans/{plan_id}", response_model=MemorizationPlanResponse)
async def update_memorization_plan(
    plan_id: str,
    payload: MemorizationPlanUpdate,
    request: Request,
    user=Depends(verify_memorization_write),
):
    service = MemorizationService(
        MemorizationRepository(request.app.state.database)
    )
    plan = await service.update_plan(
        user_id=user["_id"],
        plan_id=plan_id,
        status=payload.status,
    )

    if plan is None:
        raise HTTPException(
            status_code=404,
            detail="Memorization plan not found",
        )

    return {
        "id": str(plan["_id"]),
        "surah_number": plan["surah_number"],
        "start_ayah": plan["start_ayah"],
        "end_ayah": plan["end_ayah"],
        "status": plan["status"],
        "created_at": plan["created_at"],
        "updated_at": plan["updated_at"],
    }


def serialize_memorization_session(session):
    return {
        "id": str(session["_id"]),
        "plan_id": str(session["plan_id"]),
        "session_type": session["session_type"],
        "result": session["result"],
        "notes": session["notes"],
        "completed_at": session["completed_at"],
    }


@router.post(
    "/plans/{plan_id}/sessions",
    response_model=MemorizationSessionResponse,
    status_code=201,
)
async def create_memorization_session(
    plan_id: str,
    payload: MemorizationSessionCreate,
    request: Request,
    user=Depends(verify_memorization_write),
):
    service = MemorizationService(
        MemorizationRepository(request.app.state.database)
    )

    session = await service.create_session(
        user_id=user["_id"],
        plan_id=plan_id,
        session_type=payload.session_type,
        result=payload.result,
        notes=payload.notes,
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Memorization plan not found",
        )

    return serialize_memorization_session(session)


@router.get(
    "/plans/{plan_id}/sessions",
    response_model=list[MemorizationSessionResponse],
)
async def list_memorization_sessions(
    plan_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=50),
    user=Depends(get_current_memorization_user),
):
    service = MemorizationService(
        MemorizationRepository(request.app.state.database)
    )

    sessions = await service.list_sessions(
        user_id=user["_id"],
        plan_id=plan_id,
        limit=limit,
    )

    if sessions is None:
        raise HTTPException(
            status_code=404,
            detail="Memorization plan not found",
        )

    return [
        serialize_memorization_session(session)
        for session in sessions
    ]
