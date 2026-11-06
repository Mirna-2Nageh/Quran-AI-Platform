"""Integration tests for the persistent Quran ASR worker."""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv-asr/bin/python"
WORKER = ROOT / "models/quran-asr-small/worker.py"
SAMPLE = ROOT / "tests/audio_samples/fatiha_benchmark/001002.wav"


@pytest.mark.skipif(
    not all(p.is_file() for p in (PYTHON, WORKER, SAMPLE)),
    reason="Local ASR runtime unavailable",
)
def test_worker_recovers_and_preserves_request_ids():
    requests = [
        {"id": "first", "audio_path": str(SAMPLE)},
        {"id": "invalid", "audio_path": "/tmp/nonexistent_quran_audio.wav"},
        {"id": "last", "audio_path": str(SAMPLE)},
    ]

    result = subprocess.run(
        [str(PYTHON), str(WORKER)],
        input="".join(json.dumps(r) + "\n" for r in requests),
        capture_output=True,
        text=True,
        timeout=45,
        check=True,
        cwd=ROOT,
    )

    responses = [json.loads(line) for line in result.stdout.splitlines()]

    assert len(responses) == 3
    assert [r["id"] for r in responses] == ["first", "invalid", "last"]
    assert [r["ok"] for r in responses] == [True, False, True]

    for response in (responses[0], responses[2]):
        assert response["text"] == "الحمد لله رب العالمين"
        assert len(response["tokens"]) == len(response["timestamps"])
        assert response["timing_type"] == "asr_character_token_timestamps"
