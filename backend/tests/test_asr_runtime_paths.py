"""Regression tests for ASR runtime path resolution."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_paths(asr_root=None):
    env = os.environ.copy()
    env.pop("QURAN_AI_ASR_ROOT", None)

    if asr_root is not None:
        env["QURAN_AI_ASR_ROOT"] = str(asr_root)

    code = """
from app.services import quran_asr

print(quran_asr.PROJECT_ROOT)
print(quran_asr.ASR_PYTHON)
print(quran_asr.ASR_SCRIPT)
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )

    return result.stdout.strip().splitlines()


def test_local_asr_paths_use_repository_root():
    root, python_path, script_path = _resolve_paths()

    assert Path(root) == PROJECT_ROOT
    assert Path(python_path) == PROJECT_ROOT / ".venv-asr/bin/python"
    assert Path(script_path) == (
        PROJECT_ROOT / "models/quran-asr-small/transcribe.py"
    )


def test_docker_asr_paths_use_configured_root():
    root, python_path, script_path = _resolve_paths("/app")

    assert root == "/app"
    assert python_path == "/app/.venv-asr/bin/python"
    assert script_path == "/app/models/quran-asr-small/transcribe.py"


def test_custom_asr_root_is_supported(tmp_path):
    root, python_path, script_path = _resolve_paths(tmp_path)

    assert Path(root) == tmp_path.resolve()
    assert Path(python_path) == tmp_path / ".venv-asr/bin/python"
    assert Path(script_path) == (
        tmp_path / "models/quran-asr-small/transcribe.py"
    )
