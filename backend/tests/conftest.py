"""Isolated configuration for backend tests."""

import os
from urllib.parse import parse_qs, urlsplit

import pytest

TEST_DB_NAME = "quran_ai_ci_test"
test_uri = os.environ.get("QURAN_AI_TEST_MONGO_URI", "").strip()

if test_uri:
    parsed = urlsplit(test_uri)
    query = parse_qs(parsed.query)

    if (
        parsed.scheme != "mongodb"
        or parsed.hostname not in {"localhost", "127.0.0.1", "mongo"}
        or parsed.username != "quran_test"
        or parsed.path != f"/{TEST_DB_NAME}"
        or parsed.port not in {27017, 27018}
        or query.get("authSource") != [TEST_DB_NAME]
        or query.get("replicaSet") != ["rs0"]
    ):
        pytest.exit(
            "Refusing unsafe MongoDB integration test URI",
            returncode=2,
        )


os.environ["QURAN_AI_ENVIRONMENT"] = "testing"
os.environ["QURAN_AI_MONGO_URI"] = test_uri
os.environ["QURAN_AI_MONGO_DB_NAME"] = TEST_DB_NAME
