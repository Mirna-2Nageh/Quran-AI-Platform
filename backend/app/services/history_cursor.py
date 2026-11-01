"""Encode and decode opaque recitation history cursors."""

import base64
import json
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId

MAX_CURSOR_LENGTH = 256


class InvalidHistoryCursor(ValueError):
    """Raised when a pagination cursor is invalid."""


def encode_history_cursor(document: dict) -> str:
    created_at = document["created_at"]

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    delta = created_at.astimezone(timezone.utc) - datetime(
        1970, 1, 1, tzinfo=timezone.utc
    )
    timestamp_ms = (
        delta.days * 86_400_000
        + delta.seconds * 1000
        + delta.microseconds // 1000
    )

    payload = {
        "v": 1,
        "t": timestamp_ms,
        "id": str(document["_id"]),
    }

    raw = json.dumps(
        payload, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")

    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_history_cursor(cursor: str) -> tuple[datetime, ObjectId]:
    if not cursor or len(cursor) > MAX_CURSOR_LENGTH:
        raise InvalidHistoryCursor("Invalid pagination cursor")

    try:
        if not cursor.isascii() or any(
            char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz0123456789-_"
            for char in cursor
        ):
            raise ValueError("Invalid base64 characters")

        raw = base64.b64decode(
            cursor + "=" * (-len(cursor) % 4),
            altchars=b"-_",
            validate=True,
        )

        payload = json.loads(raw)

        if not isinstance(payload, dict):
            raise ValueError("Invalid cursor payload")

        if set(payload) != {"v", "t", "id"}:
            raise ValueError("Unexpected cursor fields")

        if type(payload["v"]) is not int or payload["v"] != 1:
            raise ValueError("Unsupported cursor version")

        timestamp_ms = payload["t"]

        if type(timestamp_ms) is not int:
            raise ValueError("Invalid timestamp")

        object_id = ObjectId(payload["id"])

        created_at = datetime(
            1970, 1, 1, tzinfo=timezone.utc
        ) + timedelta(milliseconds=timestamp_ms)

        return created_at, object_id

    except (ValueError, TypeError, OverflowError, OSError, InvalidId) as exc:
        raise InvalidHistoryCursor("Invalid pagination cursor") from exc
