from datetime import datetime
from types import SimpleNamespace

import asyncio

from app.repositories.recitation_sessions import RecitationSessionRepository


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, field, direction):
        self.documents.sort(
            key=lambda doc: doc[field],
            reverse=direction == -1,
        )
        return self

    def limit(self, value):
        self.documents = self.documents[:value]
        return self

    async def to_list(self, length):
        return self.documents[:length]


class FakeCollection:
    def __init__(self):
        self.documents = []

    async def insert_one(self, document):
        document_id = len(self.documents) + 1
        self.documents.append({**document, "_id": document_id})
        return SimpleNamespace(inserted_id=document_id)

    def find(self, query):
        return FakeCursor([
            doc.copy()
            for doc in self.documents
            if doc["user_id"] == query["user_id"]
        ])


def test_create_recitation_session():
    asyncio.run(_test_create_recitation_session())


async def _test_create_recitation_session():
    collection = FakeCollection()
    repo = RecitationSessionRepository(
        {"recitation_sessions": collection}
    )

    session = await repo.create(
        user_id="user-1",
        surah_number=1,
        ayah_number=1,
        end_ayah_number=1,
        expected_text="بسم الله",
        recognized_text="بسم الله",
        alignment={
            "expected_word_count": 2,
            "recognized_word_count": 2,
            "matched_word_count": 2,
            "issues": [],
        },
    )

    assert session["_id"] == 1
    assert session["user_id"] == "user-1"
    assert session["surah_number"] == 1
    assert session["tajweed_analyzed"] is False
    assert isinstance(session["created_at"], datetime)


def test_list_only_current_user_sessions():
    asyncio.run(_test_list_only_current_user_sessions())


async def _test_list_only_current_user_sessions():
    collection = FakeCollection()
    repo = RecitationSessionRepository(
        {"recitation_sessions": collection}
    )

    for user_id in ["user-1", "user-2", "user-1"]:
        await repo.create(
            user_id=user_id,
            surah_number=1,
            ayah_number=1,
            end_ayah_number=1,
            expected_text="بسم الله",
            recognized_text="بسم الله",
            alignment={"issues": []},
        )

    sessions = await repo.list_by_user("user-1")

    assert len(sessions) == 2
    assert all(
        session["user_id"] == "user-1"
        for session in sessions
    )
