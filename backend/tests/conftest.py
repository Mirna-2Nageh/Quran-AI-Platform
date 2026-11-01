"""Isolated configuration for backend tests."""

import os
from urllib.parse import urlsplit

import pytest

TEST_DB_NAME = "quran_ai_ci_test"
test_uri = os.environ.get("QURAN_AI_TEST_MONGO_URI", "").strip()

if test_uri:
    parsed = urlsplit(test_uri)

    if (
        parsed.scheme != "mongodb"
        or parsed.hostname not in {"localhost", "127.0.0.1"}
    ):
        pytest.exit(
            "Refusing non-local MongoDB integration test URI",
            returncode=2,
        )

os.environ["QURAN_AI_ENVIRONMENT"] = "testing"
os.environ["QURAN_AI_MONGO_URI"] = test_uri
os.environ["QURAN_AI_MONGO_DB_NAME"] = TEST_DB_NAME
