"""Persistence for in-progress live recitation sessions."""

from datetime import datetime, timezone
from uuid import uuid4


class LiveRecitationSessionRepository:
    def __init__(
        self,
        database,
        *,
        live_collection="live_recitation_sessions",
        history_collection="recitation_sessions",
    ):
        self.database = database
        self.collection = database[live_collection]
        self.history_collection = database[history_collection]

    async def create(self, *, user_id, surah_number, ayah_number, expected_text):
        now = datetime.now(timezone.utc)
        document = {
            "session_id": uuid4().hex,
            "user_id": user_id,
            "surah_number": surah_number,
            "ayah_number": ayah_number,
            "expected_text": expected_text,
            "status": "active",
            "chunks": [],
            "next_word_index": 0,
            "next_chunk_index": 0,
            "created_at": now,
            "updated_at": now,
        }
        await self.collection.insert_one(document)
        return document

    async def get_active(self, *, user_id, session_id):
        return await self.collection.find_one(
            {
                "user_id": user_id,
                "session_id": session_id,
                "status": "active",
            }
        )

    async def append_chunk(
        self,
        *,
        user_id,
        session_id,
        chunk,
        start_word_index=None,
        chunk_index=None,
        next_word_index=None,
    ):
        query = {
            "user_id": user_id,
            "session_id": session_id,
            "status": "active",
        }
        if start_word_index is not None:
            query["next_word_index"] = start_word_index
        if chunk_index is not None:
            query["next_chunk_index"] = chunk_index

        update = {
            "$push": {"chunks": chunk},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        }
        if next_word_index is not None:
            update["$set"]["next_word_index"] = next_word_index
        if chunk_index is not None:
            update["$inc"] = {"next_chunk_index": 1}

        return await self.collection.update_one(query, update)

    async def get_by_id(self, *, user_id, session_id):
        return await self.collection.find_one(
            {
                "user_id": user_id,
                "session_id": session_id,
            }
        )

    async def finalize(self, *, user_id, session_id, recitation_session_id):
        return await self.collection.update_one(
            {
                "user_id": user_id,
                "session_id": session_id,
                "status": "active",
            },
            {
                "$set": {
                    "status": "finalized",
                    "recitation_session_id": recitation_session_id,
                    "updated_at": datetime.now(timezone.utc),
                },
            },
        )

    async def finalize_atomic(self, *, client, user_id, session_id):
        """Persist a live session exactly once using a MongoDB transaction."""
        from app.ai.alignment import align_words
        from app.repositories.memorization_transactions import run_transaction

        async def operation(session):
            live = await self.collection.find_one(
                {"user_id": user_id, "session_id": session_id},
                session=session,
            )
            if live is None:
                return None
            if live["status"] == "finalized":
                return live.get("recitation_session_id")
            if live["status"] != "active":
                raise ValueError("Live session is not active")

            chunks = live.get("chunks", [])
            recognized = " ".join(
                chunk["recognized_text"]
                for chunk in chunks
                if chunk.get("recognized_text")
            ).strip()
            if not recognized:
                raise ValueError("No recognized recitation")

            expected = live["expected_text"]
            alignment = align_words(expected, recognized)

            recitation = {
                "user_id": user_id,
                "surah_number": live["surah_number"],
                "ayah_number": live["ayah_number"],
                "end_ayah_number": live["ayah_number"],
                "expected_text": expected,
                "recognized_text": recognized,
                "alignment": {
                    "expected_word_count": alignment.expected_word_count,
                    "recognized_word_count": alignment.recognized_word_count,
                    "matched_word_count": alignment.matched_word_count,
                    "issues": [
                        {
                            "operation": issue.operation,
                            "expected_word": issue.expected_word,
                            "recognized_word": issue.recognized_word,
                            "expected_index": issue.expected_index,
                            "recognized_index": issue.recognized_index,
                        }
                        for issue in alignment.issues
                    ],
                },
                "analysis_type": "chunk_based_word_alignment",
                "tajweed_analyzed": False,
                "created_at": datetime.now(timezone.utc),
            }

            saved = await self.history_collection.insert_one(
                recitation, session=session
            )

            updated = await self.collection.update_one(
                {"_id": live["_id"], "status": "active"},
                {
                    "$set": {
                        "status": "finalized",
                        "recitation_session_id": str(saved.inserted_id),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                session=session,
            )
            if updated.matched_count != 1:
                raise RuntimeError("Live session changed during finalization")
            return str(saved.inserted_id)

        return await run_transaction(client, operation)
