"""Authenticated audio recitation analysis endpoint."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.ai.alignment import align_words
from app.api.v1.auth import COOKIE_NAME, check_origin, get_auth_service
from app.schemas.recitation import AlignmentIssueResponse, AlignmentResponse
from app.repositories.recitation_sessions import RecitationSessionRepository
from app.services.auth import AuthService
from app.services.quran_asr import ASRError, transcribe_audio

router = APIRouter(prefix="/recitation", tags=["Recitation"])

MAX_AUDIO_SIZE = 10 * 1024 * 1024
MAX_EXPECTED_TEXT_LENGTH = 5000

SUPPORTED_TYPES = {"audio/webm", "audio/ogg"}


@router.post("/analyze")
async def analyze_recitation(
    request: Request,
    audio: UploadFile = File(...),
    expected_text: str = Form(...),
    surah_number: int = Form(..., ge=1, le=114),
    ayah_number: int = Form(..., ge=1),
    service: AuthService = Depends(get_auth_service),
):
    check_origin(request)

    session_token = request.cookies.get(COOKIE_NAME)
    csrf_token = request.headers.get("X-CSRF-Token")

    user = await service.get_current_user(session_token)

    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not await service.verify_csrf(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    if not expected_text.strip():
        raise HTTPException(status_code=422, detail="Expected text is required")

    if len(expected_text) > MAX_EXPECTED_TEXT_LENGTH:
        raise HTTPException(status_code=422, detail="Expected text is too long")

    content_type = (audio.content_type or "").lower()
    mime_parts = [part.strip() for part in content_type.split(";")]
    base_type = mime_parts[0]

    if base_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    if mime_parts[1:] and mime_parts[1:] != ["codecs=opus"]:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio codec parameters",
        )

    try:
        content = await audio.read(MAX_AUDIO_SIZE + 1)

        if len(content) > MAX_AUDIO_SIZE:
            raise HTTPException(status_code=413, detail="Audio exceeds 10 MB")

        if not content:
            raise HTTPException(status_code=400, detail="Audio is empty")

        valid_webm = base_type == "audio/webm" and content.startswith(
            b"\x1a\x45\xdf\xa3"
        )
        valid_ogg = base_type == "audio/ogg" and content.startswith(b"OggS")

        if not (valid_webm or valid_ogg):
            raise HTTPException(
                status_code=415,
                detail="Audio content does not match its format",
            )

        try:
            recognized_text = await transcribe_audio(content)
        except ASRError as exc:
            raise HTTPException(
                status_code=503,
                detail="Audio analysis is temporarily unavailable",
            ) from exc

        if not recognized_text:
            raise HTTPException(
                status_code=422,
                detail="No recognizable recitation detected",
            )

        result = align_words(
            expected_text=expected_text,
            recognized_text=recognized_text,
        )

        alignment = AlignmentResponse(
            expected_word_count=result.expected_word_count,
            recognized_word_count=result.recognized_word_count,
            matched_word_count=result.matched_word_count,
            issues=[
                AlignmentIssueResponse(
                    operation=issue.operation,
                    expected_word=issue.expected_word,
                    recognized_word=issue.recognized_word,
                    expected_index=issue.expected_index,
                    recognized_index=issue.recognized_index,
                )
                for issue in result.issues
            ],
        )

        repository = RecitationSessionRepository(service.database)

        saved_session = await repository.create(
            user_id=user["_id"],
            surah_number=surah_number,
            ayah_number=ayah_number,
            expected_text=expected_text,
            recognized_text=recognized_text,
            alignment=alignment.model_dump(),
        )

        return {
            "session_id": str(saved_session["_id"]),
            "recognized_text": recognized_text,
            "alignment": alignment.model_dump(),
            "analysis_type": "word_level_asr_alignment",
            "tajweed_analyzed": False,
        }

    finally:
        await audio.close()
