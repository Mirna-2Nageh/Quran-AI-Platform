"""Tests for memorization transaction retries."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.repositories.memorization_transactions import run_transaction
from pymongo.errors import OperationFailure


def make_session():
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.start_transaction = AsyncMock()
    session.commit_transaction = AsyncMock()
    session.abort_transaction = AsyncMock()
    session.in_transaction = False
    return session


@pytest.mark.asyncio
async def test_successful_commit():
    session = make_session()
    client = MagicMock()
    client.start_session = MagicMock(return_value=session)
    operation = AsyncMock(return_value="ok")

    assert await run_transaction(client, operation) == "ok"
    operation.assert_awaited_once_with(session)
    session.commit_transaction.assert_awaited_once()


@pytest.mark.asyncio
async def test_transient_error_retries_operation():
    first = make_session()
    second = make_session()

    client = MagicMock()
    client.start_session = MagicMock(side_effect=[first, second])

    error = OperationFailure(
        "Transient failure",
        112,
        details={"errorLabels": ["TransientTransactionError"]},
    )
    operation = AsyncMock(side_effect=[error, "ok"])

    assert await run_transaction(client, operation) == "ok"
    assert operation.await_count == 2
    second.commit_transaction.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_commit_retries_commit_only():
    session = make_session()
    client = MagicMock()
    client.start_session = MagicMock(return_value=session)

    error = OperationFailure(
        "Unknown commit result",
        64,
        details={"errorLabels": ["UnknownTransactionCommitResult"]},
    )
    session.commit_transaction = AsyncMock(side_effect=[error, None])
    operation = AsyncMock(return_value="created")

    assert await run_transaction(client, operation) == "created"
    operation.assert_awaited_once()
    assert session.commit_transaction.await_count == 2
