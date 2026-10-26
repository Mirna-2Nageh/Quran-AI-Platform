"""Local Quran ASR inference service."""

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

ASR_PYTHON = PROJECT_ROOT / ".venv-asr/bin/python"

ASR_SCRIPT = (
    PROJECT_ROOT / "models/quran-asr-small/transcribe.py"
)

FFMPEG_TIMEOUT_SECONDS = 30
ASR_TIMEOUT_SECONDS = 60


class ASRError(Exception):
    """Raised when audio processing or ASR inference fails."""


def _convert_audio(audio_bytes: bytes, output_path: Path) -> None:
    """Convert uploaded audio to mono 16 kHz WAV."""

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-i",
                "pipe:0",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "wav",
                str(output_path),
            ],
            input=audio_bytes,
            capture_output=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ASRError("Audio conversion failed") from exc

    if result.returncode != 0:
        raise ASRError("Invalid or unsupported audio data")


def _transcribe_sync(audio_bytes: bytes) -> str:
    """Run Quran ASR using the isolated Python environment."""

    if not ASR_PYTHON.is_file():
        raise ASRError("ASR Python environment not found")

    if not ASR_SCRIPT.is_file():
        raise ASRError("ASR model script not found")

    with tempfile.TemporaryDirectory(prefix="quran_asr_") as tmp:
        wav_path = Path(tmp) / "recitation.wav"

        _convert_audio(audio_bytes, wav_path)

        try:
            result = subprocess.run(
                [
                    str(ASR_PYTHON),
                    str(ASR_SCRIPT),
                    str(wav_path),
                    "--standard",
                ],
                capture_output=True,
                text=True,
                timeout=ASR_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ASRError("ASR inference failed") from exc

        if result.returncode != 0:
            raise ASRError("ASR model execution failed")

        return result.stdout.strip()


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Execute blocking audio processing outside the event loop."""

    return await asyncio.to_thread(
        _transcribe_sync,
        audio_bytes,
    )
