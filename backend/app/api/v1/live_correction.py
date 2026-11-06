"""Authenticated chunk-based Quran memorization correction."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.ai.alignment import align_words
from app.api.v1.auth import COOKIE_NAME, check_origin, get_auth_service
from app.repositories.live_recitation_sessions import LiveRecitationSessionRepository
from app.schemas.live_correction import LiveCorrectionResponse
from app.schemas.recitation import AlignmentIssueResponse, AlignmentResponse
from app.services.auth import AuthService
from app.services.live_audio import MAX_CHUNK_BYTES, transcribe_live_chunk
from app.services.live_correction import correct_chunk
from app.services.quran_asr import ASRError
from app.services.quran_text import QuranDatasetError, QuranTextError, get_quran_text

router = APIRouter(prefix="/recitation", tags=["Recitation"])


@router.post("/live-correction", response_model=LiveCorrectionResponse)
async def live_correction(
    request: Request,
    audio: UploadFile = File(...),
    surah_number: int = Form(..., ge=1, le=114),
    ayah_number: int = Form(..., ge=1),
    start_word_index: int = Form(default=0, ge=0),
    session_id: str | None = Form(default=None),
    chunk_index: int | None = Form(default=None, ge=0),
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

    repo = None
    if session_id is not None:
        if chunk_index is None:
            raise HTTPException(422, "chunk_index is required")

        repo = LiveRecitationSessionRepository(request.app.state.database)
        live = await repo.get_active(user_id=user["_id"], session_id=session_id)
        if live is None:
            raise HTTPException(404, "Active live session not found")
        if live["surah_number"] != surah_number or live["ayah_number"] != ayah_number:
            raise HTTPException(422, "Session verse mismatch")
        if (
            live.get("next_word_index", 0) != start_word_index
            or live.get("next_chunk_index", 0) != chunk_index
        ):
            raise HTTPException(409, "Out-of-order live chunk")

    try:
        expected_text = get_quran_text(surah_number, ayah_number, ayah_number)
    except QuranDatasetError as exc:
        raise HTTPException(
            status_code=503, detail="Quran text is temporarily unavailable"
        ) from exc
    except QuranTextError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if start_word_index >= len(expected_text.split()):
        raise HTTPException(status_code=422, detail="Invalid start word index")

    content_type = (audio.content_type or "").lower().split(";")[0].strip()
    if content_type not in {"audio/webm", "audio/ogg"}:
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    content = await audio.read(MAX_CHUNK_BYTES + 1)
    if len(content) > MAX_CHUNK_BYTES:
        raise HTTPException(status_code=413, detail="Audio chunk too large")
    if not content:
        raise HTTPException(status_code=400, detail="Audio chunk is empty")

    valid_webm = content_type == "audio/webm" and content.startswith(
        b"\x1a\x45\xdf\xa3"
    )
    valid_ogg = content_type == "audio/ogg" and content.startswith(b"OggS")

    if not (valid_webm or valid_ogg):
        raise HTTPException(status_code=415, detail="Invalid audio signature")

    manager = getattr(request.app.state, "asr_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="ASR unavailable")

    try:
        result = await transcribe_live_chunk(content, manager)
    except ASRError as exc:
        raise HTTPException(
            status_code=503, detail="Live correction temporarily unavailable"
        ) from exc

    recognized_text = result.get("text", "").strip()
    correction = correct_chunk(expected_text, recognized_text, start_word_index)

    reviewed_words = [
        item["word"] for item in correction.word_feedback if item["status"] != "pending"
    ]
    alignment_result = align_words(" ".join(reviewed_words), recognized_text)

    alignment = AlignmentResponse(
        expected_word_count=alignment_result.expected_word_count,
        recognized_word_count=alignment_result.recognized_word_count,
        matched_word_count=alignment_result.matched_word_count,
        issues=[
            AlignmentIssueResponse(
                operation=issue.operation,
                expected_word=issue.expected_word,
                recognized_word=issue.recognized_word,
                expected_index=issue.expected_index,
                recognized_index=issue.recognized_index,
            )
            for issue in alignment_result.issues
        ],
    )

    if repo is not None:
        saved = await repo.append_chunk(
            user_id=user["_id"],
            session_id=session_id,
            start_word_index=start_word_index,
            chunk_index=chunk_index,
            next_word_index=correction.next_word_index,
            chunk={
                "chunk_index": chunk_index,
                "start_word_index": start_word_index,
                "next_word_index": correction.next_word_index,
                "recognized_text": recognized_text,
            },
        )
        if saved.matched_count != 1:
            raise HTTPException(409, "Live session changed; retry required")

    return LiveCorrectionResponse(
        surah_number=surah_number,
        ayah_number=ayah_number,
        recognized_text=recognized_text,
        alignment=alignment,
        word_feedback=correction.word_feedback,
        next_word_index=correction.next_word_index,
        has_more_words=correction.has_more_words,
    )
