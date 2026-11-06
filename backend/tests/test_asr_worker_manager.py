"""Integration tests for the persistent Quran ASR manager."""

import asyncio

import pytest
from app.services.asr_worker_manager import PersistentASRManager
from app.services.quran_asr import ASR_PYTHON, ASRError

GOOD = "tests/audio_samples/fatiha_benchmark/001002.wav"
BAD = "/tmp/nonexistent_quran_audio.wav"

pytestmark = pytest.mark.skipif(
    not ASR_PYTHON.is_file(),
    reason="Local ASR runtime unavailable",
)


def test_worker_reuses_process():
    async def run():
        manager = PersistentASRManager()
        try:
            first = await manager.transcribe(GOOD)
            pid = manager._process.pid
            second = await manager.transcribe(GOOD)

            assert first["text"] == "الحمد لله رب العالمين"
            assert second["text"] == first["text"]
            assert manager._process.pid == pid
        finally:
            await manager.stop()

    asyncio.run(run())


def test_worker_recovers_after_error():
    async def run():
        manager = PersistentASRManager()
        try:
            await manager.transcribe(GOOD)

            with pytest.raises(ASRError):
                await manager.transcribe(BAD)

            assert manager._process is None

            result = await manager.transcribe(GOOD)
            assert result["text"] == "الحمد لله رب العالمين"
        finally:
            await manager.stop()

    asyncio.run(run())


def test_concurrent_requests_share_worker():
    async def run():
        manager = PersistentASRManager()
        files = [
            "tests/audio_samples/fatiha_benchmark/001002.wav",
            "tests/audio_samples/fatiha_benchmark/001003.wav",
            "tests/audio_samples/fatiha_benchmark/001004.wav",
        ]
        expected = [
            "الحمد لله رب العالمين",
            "الرحمن الرحيم",
            "ملك يوم الدين",
        ]
        try:
            results = await asyncio.gather(
                *(manager.transcribe(path) for path in files)
            )
            assert [r["text"] for r in results] == expected
            assert all(r["ok"] is True for r in results)
            assert manager._process.returncode is None
        finally:
            await manager.stop()

    asyncio.run(run())


def test_timeout_restarts_worker():
    from unittest.mock import patch

    async def run():
        manager = PersistentASRManager()
        try:
            await manager.start()
            old_pid = manager._process.pid

            with patch(
                "app.services.asr_worker_manager.WORKER_TIMEOUT_SECONDS",
                0.000001,
            ):
                with pytest.raises(ASRError):
                    await manager.transcribe(GOOD)

            assert manager._process is None

            result = await manager.transcribe(GOOD)
            assert result["text"] == "الحمد لله رب العالمين"
            assert manager._process.pid != old_pid
        finally:
            await manager.stop()

    asyncio.run(run())


def test_cancellation_cleans_up_worker():
    from unittest.mock import patch

    async def run():
        manager = PersistentASRManager()
        entered = asyncio.Event()

        async def delayed_readline():
            entered.set()
            await asyncio.sleep(30)

        try:
            await manager.start()
            old_pid = manager._process.pid

            with patch.object(
                manager._process.stdout,
                "readline",
                side_effect=delayed_readline,
            ):
                task = asyncio.create_task(manager.transcribe(GOOD))
                await asyncio.wait_for(entered.wait(), timeout=10)
                task.cancel()

                with pytest.raises(asyncio.CancelledError):
                    await task

            assert manager._process is None

            result = await manager.transcribe(GOOD)
            assert result["text"] == "الحمد لله رب العالمين"
            assert manager._process.pid != old_pid
        finally:
            await manager.stop()

    asyncio.run(run())


def test_worker_returns_valid_metadata():
    import math

    async def run():
        manager = PersistentASRManager()
        try:
            result = await manager.transcribe(GOOD)

            assert isinstance(result["text"], str)
            assert isinstance(result["tokens"], list)
            assert isinstance(result["timestamps"], list)
            assert len(result["tokens"]) == len(result["timestamps"])
            assert all(isinstance(t, str) for t in result["tokens"])

            times = result["timestamps"]
            assert all(
                isinstance(t, (int, float))
                and not isinstance(t, bool)
                and math.isfinite(t)
                and t >= 0
                for t in times
            )
            assert times == sorted(times)
            assert (
                result["timing_type"]
                == "asr_character_token_timestamps"
            )
        finally:
            await manager.stop()

    asyncio.run(run())


@pytest.mark.parametrize(
    "changes",
    [
        {"text": None},
        {"tokens": "invalid"},
        {"tokens": [123]},
        {"timestamps": [0.1, 0.2]},
        {"timestamps": [-1.0]},
        {"timestamps": [float("nan")]},
        {"timestamps": [float("inf")]},
        {"timestamps": [True]},
        {"timing_type": "unknown"},
    ],
)
def test_rejects_invalid_metadata(changes):
    from app.services.asr_worker_manager import validate_worker_metadata

    response = {
        "text": "الحمد",
        "tokens": ["الحمد"],
        "timestamps": [0.1],
        "timing_type": "asr_character_token_timestamps",
    }
    response.update(changes)

    with pytest.raises(ASRError):
        validate_worker_metadata(response)


def test_invalid_metadata_restarts_worker():
    from unittest.mock import patch

    async def run():
        manager = PersistentASRManager()
        try:
            await manager.start()
            old_pid = manager._process.pid

            with patch(
                "app.services.asr_worker_manager.validate_worker_metadata",
                side_effect=ASRError("Invalid metadata"),
            ):
                with pytest.raises(ASRError):
                    await manager.transcribe(GOOD)

            assert manager._process is None

            result = await manager.transcribe(GOOD)
            assert result["text"] == "الحمد لله رب العالمين"
            assert manager._process.pid != old_pid
        finally:
            await manager.stop()

    asyncio.run(run())
