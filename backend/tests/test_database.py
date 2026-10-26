import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.config import Settings
from app.database import close_mongo_connection, connect_to_mongo
from fastapi import FastAPI


def test_connection_is_skipped_when_uri_is_not_configured() -> None:
    app = FastAPI()
    settings = Settings(_env_file=None)

    with patch("app.database.AsyncMongoClient") as client_factory:
        asyncio.run(connect_to_mongo(app, settings))

    client_factory.assert_not_called()
    assert app.state.mongo_client is None
    assert app.state.database is None


def test_successful_connection_initializes_database_state() -> None:
    app = FastAPI()
    settings = Settings(
        _env_file=None,
        mongo_uri="mongodb://localhost:27017",
        mongo_db_name="quran_ai_test",
    )

    client = MagicMock()
    client.admin.command = AsyncMock(return_value={"ok": 1})
    client.close = AsyncMock()

    with patch("app.database.AsyncMongoClient", return_value=client):
        asyncio.run(connect_to_mongo(app, settings))

    client.admin.command.assert_awaited_once_with("ping")
    assert app.state.mongo_client is client
    assert app.state.database is client[settings.mongo_db_name]


def test_connection_failure_closes_client_and_reraises() -> None:
    app = FastAPI()
    settings = Settings(
        _env_file=None,
        mongo_uri="mongodb://localhost:27017",
    )

    client = MagicMock()
    client.admin.command = AsyncMock(side_effect=RuntimeError("MongoDB unavailable"))
    client.close = AsyncMock()

    with patch("app.database.AsyncMongoClient", return_value=client):
        with pytest.raises(RuntimeError, match="MongoDB unavailable"):
            asyncio.run(connect_to_mongo(app, settings))

    client.close.assert_awaited_once()
    assert app.state.mongo_client is None
    assert app.state.database is None


def test_shutdown_closes_client_and_clears_database_state() -> None:
    app = FastAPI()
    client = MagicMock()
    client.close = AsyncMock()

    app.state.mongo_client = client
    app.state.database = MagicMock()

    asyncio.run(close_mongo_connection(app))

    client.close.assert_awaited_once()
    assert app.state.mongo_client is None
    assert app.state.database is None
