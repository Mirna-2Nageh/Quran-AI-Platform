"""Mocks for MongoDB async transaction tests."""

from unittest.mock import AsyncMock, MagicMock


def configure_transaction(db):
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.start_transaction = AsyncMock()
    session.commit_transaction = AsyncMock()
    session.abort_transaction = AsyncMock()
    session.in_transaction = False

    db.client.start_session = MagicMock(return_value=session)
    return session
