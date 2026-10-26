from app.api.v1.audio_analysis import router as audio_analysis_router
from fastapi import APIRouter

from app.api.v1.audio import router as audio_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.recitation import router as recitation_router
from app.api.v1.recitation_history import router as recitation_history_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(recitation_router)
api_v1_router.include_router(recitation_history_router)
api_v1_router.include_router(audio_router)
api_v1_router.include_router(audio_analysis_router)
