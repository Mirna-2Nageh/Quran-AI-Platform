"""Authenticated recitation history endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.auth import COOKIE_NAME, get_auth_service
from app.repositories.recitation_sessions import RecitationSessionRepository
from app.services.auth import AuthService

router = APIRouter(prefix="/recitation", tags=["Recitation"])


@router.get("/history")
async def get_recitation_history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
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

    sessions = await repository.list_by_user(
        user_id=user["_id"],
        limit=limit,
    )

    return {
        "items": [
            {
                "id": str(session["_id"]),
                "surah_number": session["surah_number"],
                "ayah_number": session["ayah_number"],
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
    }
