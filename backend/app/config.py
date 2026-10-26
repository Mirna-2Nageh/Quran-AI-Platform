from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QURAN_AI_",
        extra="ignore",
    )

    app_name: str = "Quran AI Platform API"
    app_version: str = "0.1.0"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False

    mongo_uri: str | None = None
    mongo_db_name: str = "quran_ai"
    mongo_server_selection_timeout_ms: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()
