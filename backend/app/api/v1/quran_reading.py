"""Authenticated Quran bookmarks and reading progress API."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.auth import COOKIE_NAME, check_origin, get_auth_service
from app.repositories.quran_reading import QuranReadingRepository
from app.schemas.quran_reading import (
    BookmarkListResponse,
    BookmarkResponse,
    QuranLocation,
    ReadingProgressResponse,
)
from app.services.auth import AuthService
from app.services.quran_text import (
    QuranDatasetError,
    QuranTextError,
    validate_quran_range,
)

router = APIRouter(prefix="/quran", tags=["Quran Reading"])


async def current_user(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    token = request.cookies.get(COOKIE_NAME)
    user = await service.get_current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def write_user(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    check_origin(request)
    token = request.cookies.get(COOKIE_NAME)
    user = await service.get_current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not await service.verify_csrf(token, request.headers.get("X-CSRF-Token")):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return user


def validate_location(surah_number: int, ayah_number: int):
    try:
        validate_quran_range(surah_number, ayah_number, ayah_number)
    except QuranDatasetError as exc:
        raise HTTPException(
            status_code=503, detail="Quran dataset unavailable"
        ) from exc
    except QuranTextError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/bookmarks", response_model=BookmarkListResponse)
async def list_bookmarks(
    request: Request,
    user=Depends(current_user),
):
    repo = QuranReadingRepository(request.app.state.database)
    bookmarks = await repo.list_bookmarks(user["_id"])
    return {
        "items": [
            {
                "surah_number": item["surah_number"],
                "ayah_number": item["ayah_number"],
                "created_at": item["created_at"],
            }
            for item in bookmarks
        ],
        "count": len(bookmarks),
    }


@router.put("/bookmarks/{surah_number}/{ayah_number}", response_model=BookmarkResponse)
async def add_bookmark(
    surah_number: int,
    ayah_number: int,
    request: Request,
    user=Depends(write_user),
):
    validate_location(surah_number, ayah_number)
    repo = QuranReadingRepository(request.app.state.database)
    item = await repo.add_bookmark(user["_id"], surah_number, ayah_number)
    return {
        "surah_number": item["surah_number"],
        "ayah_number": item["ayah_number"],
        "created_at": item["created_at"],
    }


@router.delete("/bookmarks/{surah_number}/{ayah_number}")
async def delete_bookmark(
    surah_number: int,
    ayah_number: int,
    request: Request,
    user=Depends(write_user),
):
    validate_location(surah_number, ayah_number)
    repo = QuranReadingRepository(request.app.state.database)
    deleted = await repo.remove_bookmark(user["_id"], surah_number, ayah_number)
    return {"deleted": deleted}


@router.get("/progress", response_model=ReadingProgressResponse | None)
async def get_reading_progress(
    request: Request,
    user=Depends(current_user),
):
    repo = QuranReadingRepository(request.app.state.database)
    item = await repo.get_progress(user["_id"])
    if item is None:
        return None
    return {
        "surah_number": item["surah_number"],
        "ayah_number": item["ayah_number"],
        "updated_at": item["updated_at"],
    }


@router.put("/progress", response_model=ReadingProgressResponse)
async def save_reading_progress(
    location: QuranLocation,
    request: Request,
    user=Depends(write_user),
):
    validate_location(location.surah_number, location.ayah_number)
    repo = QuranReadingRepository(request.app.state.database)
    item = await repo.save_progress(
        user["_id"], location.surah_number, location.ayah_number
    )
    return {
        "surah_number": item["surah_number"],
        "ayah_number": item["ayah_number"],
        "updated_at": item["updated_at"],
    }
