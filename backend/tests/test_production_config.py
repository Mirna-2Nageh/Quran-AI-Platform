import pytest
from app.config import Settings
from pydantic import ValidationError


def test_production_rejects_missing_mongo_uri():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            mongo_uri=None,
            allowed_origins=["https://example.com"],
        )


def test_production_rejects_http_origin():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            mongo_uri="mongodb://localhost:27017",
            allowed_origins=["http://example.com"],
        )


def test_production_rejects_localhost_origin():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            mongo_uri="mongodb://localhost:27017",
            allowed_origins=["https://localhost:5173"],
        )


def test_production_accepts_https_origin():
    settings = Settings(
        _env_file=None,
        environment="production",
        mongo_uri="mongodb://localhost:27017",
        allowed_origins=["https://example.com"],
    )

    assert settings.environment == "production"
