from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.config import get_settings
from app.database import close_mongo_connection, connect_to_mongo

settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    await connect_to_mongo(application, settings)

    try:
        yield
    finally:
        await close_mongo_connection(application)


app = FastAPI(
    title=settings.app_name,
    description="Backend API for the Quran AI learning platform.",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Return the application health status."""
    return {"status": "ok"}
