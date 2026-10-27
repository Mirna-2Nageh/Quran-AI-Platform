"""Tests for the Quran dataset setup script."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "setup_quran_dataset.py"
)

spec = importlib.util.spec_from_file_location(
    "setup_quran_dataset", SCRIPT
)
setup = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(setup)


def test_existing_dataset_verification():
    with patch.object(sys, "argv", ["setup", "--verify-only"]):
        assert setup.main() == 0


def test_missing_dataset_rejected(tmp_path):
    with (
        patch.object(setup, "OUTPUT", tmp_path / "missing.json"),
        patch.object(sys, "argv", ["setup", "--verify-only"]),
    ):
        assert setup.main() == 1


def test_existing_dataset_not_overwritten(tmp_path):
    target = tmp_path / "uthmani.json"
    target.write_text("existing content", encoding="utf-8")

    with (
        patch.object(setup, "OUTPUT", target),
        patch.object(sys, "argv", ["setup"]),
    ):
        assert setup.main() == 1

    assert target.read_text(encoding="utf-8") == "existing content"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"code": 500},
        {"code": 200, "data": {}},
        {
            "code": 200,
            "data": {
                "edition": {"identifier": "wrong-edition"},
                "surahs": [],
            },
        },
        {
            "code": 200,
            "data": {
                "edition": {
                    "identifier": setup.EDITION,
                },
                "surahs": [],
            },
        },
    ],
)
def test_invalid_api_payload_rejected(payload):
    with pytest.raises(ValueError):
        setup.build_dataset(payload)


def test_checksum_mismatch_rejected(tmp_path):
    target = tmp_path / "uthmani.json"

    with (
        patch.object(setup, "OUTPUT", target),
        patch.object(sys, "argv", ["setup", "--verify-only"]),
    ):
        target.write_bytes(b"tampered")
        assert setup.main() == 1


def test_dataset_serialization_matches_pinned_hash():
    dataset = json.loads(setup.OUTPUT.read_text(encoding="utf-8"))

    encoded = (
        json.dumps(
            dataset,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")

    import hashlib

    assert hashlib.sha256(encoded).hexdigest() == setup.EXPECTED_SHA256
