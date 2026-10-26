from functools import lru_cache
from typing import Literal

from pydantic import model_validator
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

    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    mongo_uri: str | None = None
    mongo_db_name: str = "quran_ai"
    mongo_server_selection_timeout_ms: int = 5000

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.environment != "production":
            return self

        if not self.mongo_uri:
            raise ValueError("MongoDB URI is required in production")

        if not self.allowed_origins:
            raise ValueError("Allowed origins are required in production")

        for origin in self.allowed_origins:
            if not origin.startswith("https://"):
                raise ValueError("Production origins must use HTTPS")

            if "localhost" in origin or "127.0.0.1" in origin:
                raise ValueError("Localhost origins are not allowed in production")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
