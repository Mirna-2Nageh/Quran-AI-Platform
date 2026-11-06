"""Audio preparation for chunk-based live memorization correction."""

import asyncio
import subprocess
import tempfile
import wave
from pathlib import Path

from app.services.quran_asr import ASRError

MAX_CHUNK_BYTES = 5 * 1024 * 1024
MAX_WAV_BYTES = 1_000_000
MAX_CHUNK_SECONDS = 30


def _prepare_wav(audio_bytes: bytes, wav_path: Path) -> None:
    """Convert audio and validate the resulting PCM WAV."""
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-nostdin",
                "-y",
                "-protocol_whitelist", "pipe,file",
                "-i", "pipe:0",
                "-t", str(MAX_CHUNK_SECONDS),
                "-ac", "1",
                "-ar", "16000",
                "-acodec", "pcm_s16le",
                "-f", "wav",
                "-fs", str(MAX_WAV_BYTES),
                str(wav_path),
            ],
            input=audio_bytes,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ASRError("Audio conversion failed") from exc

    if result.returncode != 0:
        raise ASRError("Invalid or unsupported audio data")

    if wav_path.stat().st_size > MAX_WAV_BYTES:
        raise ASRError("Audio chunk is too large")

    try:
        with wave.open(str(wav_path), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
            valid = (
                wav.getnchannels() == 1
                and wav.getframerate() == 16000
                and wav.getsampwidth() == 2
                and 0 < duration <= MAX_CHUNK_SECONDS
            )
    except (OSError, EOFError, wave.Error, ZeroDivisionError) as exc:
        raise ASRError("Invalid converted audio") from exc

    if not valid:
        raise ASRError("Invalid audio duration or format")


async def transcribe_live_chunk(audio_bytes: bytes, manager):
    """Transcribe a backend-owned temporary WAV."""
    if not audio_bytes or len(audio_bytes) > MAX_CHUNK_BYTES:
        raise ASRError("Invalid audio chunk size")

    with tempfile.TemporaryDirectory(prefix="quran_live_") as tmp:
        wav_path = Path(tmp) / "chunk.wav"
        conversion = asyncio.create_task(
            asyncio.to_thread(_prepare_wav, audio_bytes, wav_path)
        )
        try:
            await asyncio.shield(conversion)
        except asyncio.CancelledError:
            while not conversion.done():
                try:
                    await asyncio.shield(conversion)
                except asyncio.CancelledError:
                    continue

            if not conversion.cancelled():
                conversion.exception()

            raise

        return await manager.transcribe(wav_path)
