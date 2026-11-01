"""Regression tests for local Quran ASR runtime failures."""

import subprocess
from unittest.mock import patch

import pytest
from app.services.quran_asr import (
    ASRError,
    _convert_audio,
    _transcribe_metadata_sync,
)


@pytest.mark.parametrize(
    ("failure", "expected_message"),
    [
        (
            subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=30),
            "Audio conversion failed",
        ),
        (
            FileNotFoundError("ffmpeg not installed"),
            "Audio conversion failed",
        ),
    ],
)
def test_ffmpeg_runtime_failures(failure, expected_message, tmp_path):
    output = tmp_path / "audio.wav"

    with patch(
        "app.services.quran_asr.subprocess.run",
        side_effect=failure,
    ):
        with pytest.raises(ASRError, match=expected_message):
            _convert_audio(b"fake-audio", output)


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.TimeoutExpired(cmd=["asr"], timeout=60),
        OSError("private model runtime failure"),
    ],
)
def test_asr_runtime_failures(failure):
    with (
        patch("app.services.quran_asr.ASR_PYTHON") as python_path,
        patch("app.services.quran_asr.ASR_SCRIPT") as script_path,
        patch("app.services.quran_asr._convert_audio"),
        patch(
            "app.services.quran_asr.subprocess.run",
            side_effect=failure,
        ),
    ):
        python_path.is_file.return_value = True
        script_path.is_file.return_value = True

        with pytest.raises(ASRError, match="ASR inference failed"):
            _transcribe_metadata_sync(b"fake-audio")


@pytest.mark.parametrize(
    ("missing_dependency", "expected_message"),
    [
        ("python", "ASR Python environment not found"),
        ("script", "ASR model script not found"),
    ],
)
def test_missing_asr_dependencies(missing_dependency, expected_message):
    with (
        patch("app.services.quran_asr.ASR_PYTHON") as python_path,
        patch("app.services.quran_asr.ASR_SCRIPT") as script_path,
        patch("app.services.quran_asr._convert_audio") as convert,
        patch("app.services.quran_asr.subprocess.run") as run,
    ):
        python_path.is_file.return_value = missing_dependency != "python"
        script_path.is_file.return_value = missing_dependency != "script"

        with pytest.raises(ASRError, match=expected_message):
            _transcribe_metadata_sync(b"fake-audio")

        convert.assert_not_called()
        run.assert_not_called()
