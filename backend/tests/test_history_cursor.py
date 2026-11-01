"""Tests for recitation history cursor encoding and validation."""

from datetime import datetime, timezone

import pytest
from app.services.history_cursor import (
    InvalidHistoryCursor,
    decode_history_cursor,
    encode_history_cursor,
)
from bson import ObjectId


def test_cursor_round_trip():
    document = {
        "_id": ObjectId(),
        "created_at": datetime(
            2026, 11, 1, 13, 0, 0, 123000,
            tzinfo=timezone.utc,
        ),
    }

    token = encode_history_cursor(document)
    created_at, object_id = decode_history_cursor(token)

    assert created_at == document["created_at"]
    assert object_id == document["_id"]


@pytest.mark.parametrize(
    "token",
    [
        "",
        "not-valid!",
        "a" * 257,
        "e30",
        "bnVsbA",
    ],
)
def test_invalid_cursors_rejected(token):
    with pytest.raises(InvalidHistoryCursor):
        decode_history_cursor(token)


def test_cursor_rejects_invalid_object_id():
    import base64
    import json

    payload = {
        "v": 1,
        "t": 1793538000000,
        "id": "invalid-object-id",
    }

    raw = json.dumps(payload).encode("utf-8")
    token = base64.urlsafe_b64encode(raw).decode().rstrip("=")

    with pytest.raises(InvalidHistoryCursor):
        decode_history_cursor(token)
