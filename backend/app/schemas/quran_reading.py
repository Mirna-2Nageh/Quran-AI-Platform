"""API schemas for Quran bookmarks and reading progress."""

from datetime import datetime

from pydantic import BaseModel, Field


class QuranLocation(BaseModel):
    surah_number: int = Field(ge=1, le=114)
    ayah_number: int = Field(ge=1)


class BookmarkResponse(QuranLocation):
    created_at: datetime


class BookmarkListResponse(BaseModel):
    items: list[BookmarkResponse]
    count: int


class ReadingProgressResponse(QuranLocation):
    updated_at: datetime
