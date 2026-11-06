import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.services.live_audio import transcribe_live_chunk
from app.services.quran_asr import ASRError


def sample_audio():
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\\x00\\x00" * 16000)

    return buffer.getvalue()


def test_live_audio_success_and_cleanup():
    async def run():
        captured = []

        async def fake_transcribe(path):
            captured.append(Path(path))
            assert path.is_file()
            return {"text": "الحمد لله رب العالمين"}

        manager = AsyncMock()
        manager.transcribe.side_effect = fake_transcribe

        result = await transcribe_live_chunk(sample_audio(), manager)

        assert result["text"] == "الحمد لله رب العالمين"
        assert len(captured) == 1
        assert not captured[0].exists()

    asyncio.run(run())


def test_live_audio_failure_cleanup():
    async def run():
        captured = []

        async def fake_transcribe(path):
            captured.append(Path(path))
            assert path.is_file()
            raise ASRError("ASR failed")

        manager = AsyncMock()
        manager.transcribe.side_effect = fake_transcribe

        with pytest.raises(ASRError, match="ASR failed"):
            await transcribe_live_chunk(sample_audio(), manager)

        assert len(captured) == 1
        assert not captured[0].exists()

    asyncio.run(run())


@pytest.mark.parametrize("audio", [b"", b"x" * (5 * 1024 * 1024 + 1)])
def test_live_audio_rejects_invalid_size(audio):
    async def run():
        manager = AsyncMock()

        with pytest.raises(ASRError, match="Invalid audio chunk size"):
            await transcribe_live_chunk(audio, manager)

        manager.transcribe.assert_not_awaited()

    asyncio.run(run())


def test_live_audio_ffmpeg_timeout(tmp_path):
    import subprocess
    from unittest.mock import patch

    from app.services.live_audio import _prepare_wav

    with patch(
        "app.services.live_audio.subprocess.run",
        side_effect=subprocess.TimeoutExpired("ffmpeg", 15),
    ):
        with pytest.raises(ASRError, match="Audio conversion failed"):
            _prepare_wav(b"audio", tmp_path / "chunk.wav")


def test_live_audio_rejects_oversized_output(tmp_path):
    from unittest.mock import patch

    from app.services.live_audio import MAX_WAV_BYTES, _prepare_wav

    def fake_conversion(*args, **kwargs):
        (tmp_path / "chunk.wav").write_bytes(b"x" * (MAX_WAV_BYTES + 1))
        return type("Result", (), {"returncode": 0})()

    with patch(
        "app.services.live_audio.subprocess.run",
        side_effect=fake_conversion,
    ):
        with pytest.raises(ASRError, match="Audio chunk is too large"):
            _prepare_wav(b"audio", tmp_path / "chunk.wav")


def test_live_audio_rejects_long_duration(tmp_path):
    import wave
    from unittest.mock import patch

    from app.services.live_audio import _prepare_wav

    def fake_conversion(*args, **kwargs):
        with wave.open(str(tmp_path / "chunk.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * (31 * 16000))

        return type("Result", (), {"returncode": 0})()

    with patch(
        "app.services.live_audio.subprocess.run",
        side_effect=fake_conversion,
    ):
        with pytest.raises(ASRError, match="Invalid audio duration or format"):
            _prepare_wav(b"audio", tmp_path / "chunk.wav")


def test_live_audio_cancellation_waits_for_conversion():
    import threading
    from unittest.mock import patch

    from app.services import live_audio

    async def run():
        started = threading.Event()
        release = threading.Event()
        captured = []

        def slow_conversion(audio, path):
            captured.append(Path(path))
            started.set()
            if not release.wait(timeout=5):
                raise RuntimeError("Test conversion timed out")

        manager = AsyncMock()

        with patch.object(live_audio, "_prepare_wav", slow_conversion):
            task = asyncio.create_task(
                live_audio.transcribe_live_chunk(b"audio", manager)
            )

            try:
                await asyncio.wait_for(
                    asyncio.to_thread(started.wait, 2),
                    timeout=3,
                )
                assert started.is_set()

                task.cancel()
                await asyncio.sleep(0.05)

                assert not task.done()
                assert captured[0].parent.exists()
            finally:
                release.set()

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=5)

        assert not captured[0].parent.exists()
        manager.transcribe.assert_not_awaited()

    asyncio.run(run())


def test_live_audio_repeated_cancellation():
    import threading
    from unittest.mock import patch

    from app.services import live_audio

    async def run():
        started = threading.Event()
        release = threading.Event()
        captured = []

        def slow_conversion(audio, path):
            captured.append(Path(path))
            started.set()
            if not release.wait(timeout=5):
                raise RuntimeError("Conversion timed out")

        manager = AsyncMock()

        with patch.object(live_audio, "_prepare_wav", slow_conversion):
            task = asyncio.create_task(
                live_audio.transcribe_live_chunk(b"audio", manager)
            )

            try:
                assert await asyncio.to_thread(started.wait, 2)

                task.cancel()
                await asyncio.sleep(0.02)
                task.cancel()
                await asyncio.sleep(0.02)

                assert not task.done()
                assert captured[0].exists() is False
                assert captured[0].parent.exists()
            finally:
                release.set()

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=5)

        assert not captured[0].parent.exists()
        manager.transcribe.assert_not_awaited()

    asyncio.run(run())
