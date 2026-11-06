"""Transaction utilities for memorization operations."""

import asyncio

from pymongo.errors import PyMongoError


async def run_transaction(client, operation, *, max_attempts=3):
    """Retry transient transactions without replaying uncertain commits."""
    for attempt in range(max_attempts):
        async with client.start_session() as session:
            await session.start_transaction()
            try:
                result = await operation(session)
                for commit_attempt in range(5):
                    try:
                        await session.commit_transaction()
                        return result
                    except PyMongoError as exc:
                        if not exc.has_error_label("UnknownTransactionCommitResult"):
                            raise
                        if commit_attempt == 4:
                            raise
                        await asyncio.sleep(0.05)
                raise RuntimeError("Commit retry limit exceeded")
            except PyMongoError as exc:
                if session.in_transaction:
                    await session.abort_transaction()
                if (
                    not exc.has_error_label("TransientTransactionError")
                    or attempt == max_attempts - 1
                ):
                    raise
                await asyncio.sleep(0.05 * (attempt + 1))
            except BaseException:
                if session.in_transaction:
                    await session.abort_transaction()
                raise

    raise RuntimeError("Transaction retry limit exceeded")
