"""Lifecycle manager for the persistent local Quran ASR worker."""

import asyncio
import json
import math
import uuid

from app.services.quran_asr import ASR_PYTHON, PROJECT_ROOT, ASRError

WORKER_TIMEOUT_SECONDS = 60

WORKER_SCRIPT = PROJECT_ROOT / "models/quran-asr-small/worker.py"


def validate_worker_metadata(response):
    """Validate transcription metadata returned by the ASR worker."""
    if not isinstance(response.get("text"), str):
        raise ASRError("Invalid ASR text")

    tokens = response.get("tokens")
    times = response.get("timestamps")

    if not isinstance(tokens, list) or not all(
        isinstance(token, str) for token in tokens
    ):
        raise ASRError("Invalid ASR tokens")

    if not isinstance(times, list) or len(tokens) != len(times):
        raise ASRError("Invalid ASR timestamps")

    if any(
        isinstance(t, bool)
        or not isinstance(t, (int, float))
        or not math.isfinite(t)
        or t < 0
        for t in times
    ):
        raise ASRError("Invalid ASR timestamp values")

    if times != sorted(times):
        raise ASRError("Unsorted ASR timestamps")

    if response.get("timing_type") != "asr_character_token_timestamps":
        raise ASRError("Unsupported ASR timing type")


class PersistentASRManager:
    """Serialize requests to a persistent ASR subprocess."""

    def __init__(self):
        self._process = None
        self._lock = asyncio.Lock()

    async def start(self):
        async with self._lock:
            await self._start_unlocked()

    async def _start_unlocked(self):
        if self._process is not None and self._process.returncode is None:
            return

        if not ASR_PYTHON.is_file() or not WORKER_SCRIPT.is_file():
            raise ASRError("Persistent ASR runtime unavailable")

        self._process = await asyncio.create_subprocess_exec(
            str(ASR_PYTHON),
            str(WORKER_SCRIPT),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=str(PROJECT_ROOT),
        )

    async def stop(self):
        """Terminate the worker and release its resources."""
        async with self._lock:
            await self._stop_unlocked()

    async def _stop_unlocked(self):
        process = self._process
        self._process = None

        if process is None:
            return

        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        else:
            await process.wait()

    async def transcribe(self, audio_path):
        """Transcribe one WAV file through the persistent worker."""
        async with self._lock:
            await self._start_unlocked()
            process = self._process
            request_id = uuid.uuid4().hex

            request = {
                "id": request_id,
                "audio_path": str(audio_path),
            }

            try:
                process.stdin.write(
                    (json.dumps(request) + "\n").encode("utf-8")
                )
                await asyncio.wait_for(
                    process.stdin.drain(),
                    timeout=WORKER_TIMEOUT_SECONDS,
                )
                line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=WORKER_TIMEOUT_SECONDS,
                )
                if not line:
                    raise ASRError("ASR worker closed unexpectedly")

                response = json.loads(line)
                if (
                    not isinstance(response, dict)
                    or response.get("id") != request_id
                    or response.get("ok") is not True
                ):
                    raise ASRError("Invalid ASR worker response")

                validate_worker_metadata(response)
                return response
            except (Exception, asyncio.CancelledError) as exc:
                await self._stop_unlocked()
                if isinstance(exc, asyncio.CancelledError):
                    raise
                raise ASRError("ASR worker request failed") from exc
