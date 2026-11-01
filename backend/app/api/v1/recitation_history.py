"""Authenticated recitation history endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.auth import COOKIE_NAME, get_auth_service
from app.repositories.recitation_sessions import RecitationSessionRepository
from app.schemas.recitation_api import RecitationHistoryResponse
from app.services.auth import AuthService
from app.services.history_cursor import (
    InvalidHistoryCursor,
    decode_history_cursor,
    encode_history_cursor,
)

router = APIRouter(prefix="/recitation", tags=["Recitation"])


@router.get("/history", response_model=RecitationHistoryResponse)
async def get_recitation_history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None, max_length=256),
    service: AuthService = Depends(get_auth_service),
):
    session_token = request.cookies.get(COOKIE_NAME)
    user = await service.get_current_user(session_token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    repository = RecitationSessionRepository(service.database)

    try:
        after = decode_history_cursor(cursor) if cursor is not None else None
    except InvalidHistoryCursor as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid pagination cursor",
        ) from exc

    sessions, has_more = await repository.list_page_by_user(
        user_id=user["_id"],
        limit=limit,
        after=after,
    )

    next_cursor = (
        encode_history_cursor(sessions[-1])
        if has_more and sessions
        else None
    )

    return {
        "items": [
            {
                "id": str(session["_id"]),
                "surah_number": session["surah_number"],
                "ayah_number": session["ayah_number"],
                "end_ayah_number": session.get(
                    "end_ayah_number", session["ayah_number"]
                ),
                "expected_text": session["expected_text"],
                "recognized_text": session["recognized_text"],
                "alignment": session["alignment"],
                "analysis_type": session["analysis_type"],
                "tajweed_analyzed": session["tajweed_analyzed"],
                "created_at": session["created_at"],
            }
            for session in sessions
        ],
        "count": len(sessions),
        "has_more": has_more,
        "next_cursor": next_cursor,
    }
