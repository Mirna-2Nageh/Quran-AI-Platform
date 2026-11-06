"""Lifecycle endpoints for persistent live recitation."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.v1.auth import COOKIE_NAME, check_origin, get_auth_service
from app.repositories.live_recitation_sessions import LiveRecitationSessionRepository
from app.services.auth import AuthService
from app.services.quran_text import QuranDatasetError, QuranTextError, get_quran_text

router = APIRouter(prefix="/recitation/live-sessions", tags=["Recitation"])


class StartLiveSessionRequest(BaseModel):
    surah_number: int = Field(ge=1, le=114)
    ayah_number: int = Field(ge=1)


async def authenticated_user(request: Request, service: AuthService):
    check_origin(request)
    token = request.cookies.get(COOKIE_NAME)
    user = await service.get_current_user(token)
    if user is None:
        raise HTTPException(401, "Not authenticated")
    if not await service.verify_csrf(token, request.headers.get("X-CSRF-Token")):
        raise HTTPException(403, "Invalid CSRF token")
    return user


@router.post("/start")
async def start_live_session(
    payload: StartLiveSessionRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    user = await authenticated_user(request, service)

    try:
        expected_text = get_quran_text(
            payload.surah_number, payload.ayah_number, payload.ayah_number
        )
    except QuranDatasetError as exc:
        raise HTTPException(503, "Quran text temporarily unavailable") from exc
    except QuranTextError as exc:
        raise HTTPException(422, str(exc)) from exc

    repo = LiveRecitationSessionRepository(request.app.state.database)
    live = await repo.create(
        user_id=user["_id"],
        surah_number=payload.surah_number,
        ayah_number=payload.ayah_number,
        expected_text=expected_text,
    )
    return {"session_id": live["session_id"], "status": "active"}


@router.post("/{session_id}/finalize")
async def finalize_live_session(
    session_id: str,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    user = await authenticated_user(request, service)
    repo = LiveRecitationSessionRepository(request.app.state.database)

    try:
        recitation_id = await repo.finalize_atomic(
            client=request.app.state.mongo_client,
            user_id=user["_id"],
            session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    if recitation_id is None:
        raise HTTPException(404, "Live session not found")

    return {
        "session_id": session_id,
        "recitation_session_id": recitation_id,
        "status": "finalized",
    }
