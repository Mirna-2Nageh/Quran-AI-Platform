import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from app.main import lifespan
from app.services.asr_worker_manager import PersistentASRManager
from fastapi import FastAPI


def test_asr_manager_lifecycle():
    async def run():
        application = FastAPI()

        with (
            patch("app.main.connect_to_mongo", new_callable=AsyncMock) as connect,
            patch("app.main.close_mongo_connection", new_callable=AsyncMock) as close,
        ):
            async with lifespan(application):
                manager = application.state.asr_manager
                assert isinstance(manager, PersistentASRManager)
                assert manager._process is None
                connect.assert_awaited_once()

            assert manager._process is None
            close.assert_awaited_once_with(application)

    asyncio.run(run())


def test_asr_shutdown_failure_still_closes_mongo():
    async def run():
        application = FastAPI()

        with (
            patch("app.main.connect_to_mongo", new_callable=AsyncMock),
            patch("app.main.close_mongo_connection", new_callable=AsyncMock) as close,
            patch.object(
                PersistentASRManager,
                "stop",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Shutdown failed"),
            ),
        ):
            with pytest.raises(RuntimeError, match="Shutdown failed"):
                async with lifespan(application):
                    pass

            close.assert_awaited_once_with(application)

    asyncio.run(run())


def test_mongo_startup_failure_cleans_up():
    async def run():
        application = FastAPI()

        with (
            patch(
                "app.main.connect_to_mongo",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Mongo unavailable"),
            ),
            patch("app.main.close_mongo_connection", new_callable=AsyncMock) as close,
            patch.object(
                PersistentASRManager,
                "stop",
                new_callable=AsyncMock,
            ) as stop,
        ):
            with pytest.raises(RuntimeError, match="Mongo unavailable"):
                async with lifespan(application):
                    pass

            stop.assert_awaited_once()
            close.assert_awaited_once_with(application)

    asyncio.run(run())
