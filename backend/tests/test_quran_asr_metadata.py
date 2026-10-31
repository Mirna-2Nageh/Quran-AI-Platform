"""Tests for Quran ASR metadata subprocess integration."""

import json
import subprocess
from unittest.mock import patch

import pytest

from app.services.quran_asr import (
    ASRError,
    ASRMetadata,
    _transcribe_metadata_sync,
)


VALID_PAYLOAD = {
    "text": "بسم الله",
    "tokens": ["ب", "س", "م", " ", "ا", "ل", "ل", "ه"],
    "timestamps": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    "timing_type": "asr_character_token_timestamps",
}


def _run_with_output(output, returncode=0):
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=output,
        stderr="",
    )

    with (
        patch("app.services.quran_asr.ASR_PYTHON") as python_path,
        patch("app.services.quran_asr.ASR_SCRIPT") as script_path,
        patch("app.services.quran_asr._convert_audio"),
        patch("app.services.quran_asr.subprocess.run", return_value=completed),
    ):
        python_path.is_file.return_value = True
        script_path.is_file.return_value = True
        return _transcribe_metadata_sync(b"fake-audio")


def test_valid_metadata():
    result = _run_with_output(json.dumps(VALID_PAYLOAD))

    assert isinstance(result, ASRMetadata)
    assert result.text == "بسم الله"
    assert len(result.tokens) == len(result.timestamps) == 8
    assert result.timing_type == "asr_character_token_timestamps"


def test_invalid_json():
    with pytest.raises(ASRError, match="Invalid ASR metadata output"):
        _run_with_output("not-json")


def test_mismatched_token_and_timestamp_counts():
    payload = {**VALID_PAYLOAD, "timestamps": [0.1]}

    with pytest.raises(ASRError, match="Invalid ASR metadata values"):
        _run_with_output(json.dumps(payload))


@pytest.mark.parametrize("timestamp", [-1, float("nan"), float("inf"), True])
def test_invalid_timestamp_values(timestamp):
    payload = {
        **VALID_PAYLOAD,
        "timestamps": [timestamp] * len(VALID_PAYLOAD["tokens"]),
    }

    with pytest.raises(ASRError, match="Invalid ASR metadata values"):
        _run_with_output(json.dumps(payload))


def test_unsorted_timestamps():
    payload = {
        **VALID_PAYLOAD,
        "timestamps": [0.2, 0.1, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    }

    with pytest.raises(ASRError, match="Invalid ASR metadata values"):
        _run_with_output(json.dumps(payload))


def test_subprocess_failure():
    with pytest.raises(ASRError, match="ASR model execution failed"):
        _run_with_output("", returncode=1)
