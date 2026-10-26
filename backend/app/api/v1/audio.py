from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.api.v1.auth import (
    COOKIE_NAME,
    check_origin,
    get_auth_service,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/recitation", tags=["Recitation"])

MAX_AUDIO_SIZE = 10 * 1024 * 1024

SUPPORTED_TYPES = {
    "audio/webm",
    "audio/ogg",
}


@router.post("/audio")
async def upload_recitation_audio(
    request: Request,
    audio: UploadFile = File(...),
    service: AuthService = Depends(get_auth_service),
):
    check_origin(request)

    session_token = request.cookies.get(COOKIE_NAME)
    csrf_token = request.headers.get("X-CSRF-Token")

    user = await service.get_current_user(session_token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    if not await service.verify_csrf(session_token, csrf_token):
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token",
        )

    raw_content_type = audio.content_type or ""
    mime_parts = raw_content_type.lower().split(";")
    base_content_type = mime_parts[0].strip()

    if base_content_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio format",
        )

    parameters = [part.strip() for part in mime_parts[1:]]

    if parameters and parameters != ["codecs=opus"]:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio codec parameters",
        )

    try:
        content = await audio.read(MAX_AUDIO_SIZE + 1)

        if len(content) > MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Audio file exceeds 10 MB",
            )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty",
            )

        is_webm = content.startswith(b"\x1a\x45\xdf\xa3")
        is_ogg = content.startswith(b"OggS")

        valid_format = (
            base_content_type == "audio/webm" and is_webm
        ) or (
            base_content_type == "audio/ogg" and is_ogg
        )

        if not valid_format:
            raise HTTPException(
                status_code=415,
                detail="Audio content does not match its format",
            )

        return {
            "message": "Audio received successfully",
            "filename": audio.filename,
            "content_type": audio.content_type,
            "size_bytes": len(content),
            "stored": False,
            "analyzed": False,
        }
    finally:
        await audio.close()
