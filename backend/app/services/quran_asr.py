"""Local Quran ASR inference service."""

import asyncio
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from app.ai.word_timing import WordTiming, estimate_word_timings


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


@dataclass(frozen=True)
class ASRMetadata:
    """ASR text and raw character-token timestamps."""

    text: str
    tokens: list[str]
    timestamps: list[float]
    timing_type: str
    word_timings: list[WordTiming] = field(default_factory=list)


def _transcribe_metadata_sync(audio_bytes: bytes) -> ASRMetadata:
    """Run ASR with JSON output in the isolated environment."""

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
                    "--json",
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

        try:
            payload = json.loads(result.stdout)
        except (ValueError, TypeError) as exc:
            raise ASRError("Invalid ASR metadata output") from exc

        if not isinstance(payload, dict):
            raise ASRError("Invalid ASR metadata structure")

        text = payload.get("text")
        tokens = payload.get("tokens")
        timestamps = payload.get("timestamps")
        timing_type = payload.get("timing_type")

        if (
            not isinstance(text, str)
            or not isinstance(tokens, list)
            or not isinstance(timestamps, list)
            or timing_type != "asr_character_token_timestamps"
            or len(tokens) != len(timestamps)
            or any(not isinstance(token, str) for token in tokens)
            or any(
                isinstance(t, bool)
                or not isinstance(t, (int, float))
                or not math.isfinite(t)
                or t < 0
                for t in timestamps
            )
            or any(a > b for a, b in zip(timestamps, timestamps[1:]))
        ):
            raise ASRError("Invalid ASR metadata values")

        try:
            word_timings = estimate_word_timings(
                text=text,
                tokens=tokens,
                timestamps=timestamps,
            )
        except ValueError:
            word_timings = []

        return ASRMetadata(
            text=text,
            tokens=tokens,
            timestamps=[float(t) for t in timestamps],
            timing_type=timing_type,
            word_timings=word_timings,
        )


async def transcribe_audio_with_metadata(audio_bytes: bytes) -> ASRMetadata:
    """Return ASR transcription and character-token timestamps."""

    return await asyncio.to_thread(
        _transcribe_metadata_sync,
        audio_bytes,
    )
