import pytest
from app.schemas.memorization import MemorizationSessionCreate
from bson import ObjectId
from pydantic import ValidationError


def test_session_without_recitation_id_is_valid():
    session = MemorizationSessionCreate(
        session_type="memorization",
        result="completed",
    )
    assert session.recitation_session_id is None


def test_session_with_valid_recitation_id():
    session_id = str(ObjectId())
    session = MemorizationSessionCreate(
        session_type="revision",
        result="needs_review",
        recitation_session_id=session_id,
    )
    assert session.recitation_session_id == session_id


def test_session_rejects_invalid_recitation_id():
    with pytest.raises(ValidationError):
        MemorizationSessionCreate(
            session_type="memorization",
            result="completed",
            recitation_session_id="invalid-id",
        )
