import logging

from fastapi import FastAPI
from pymongo import AsyncMongoClient

from app.config import Settings

logger = logging.getLogger(__name__)


async def connect_to_mongo(app: FastAPI, settings: Settings) -> None:
    """Connect to MongoDB when a URI is configured."""
    app.state.mongo_client = None
    app.state.database = None

    if not settings.mongo_uri:
        logger.info("MongoDB URI is not configured; skipping connection.")
        return

    client = AsyncMongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=(settings.mongo_server_selection_timeout_ms),
    )

    try:
        await client.admin.command("ping")
    except Exception:
        await client.close()
        logger.exception("Failed to connect to MongoDB.")
        raise

    app.state.mongo_client = client
    app.state.database = client[settings.mongo_db_name]

    await app.state.database["users"].create_index("email", unique=True)
    await app.state.database["sessions"].create_index("token_hash", unique=True)
    await app.state.database["sessions"].create_index(
        "expires_at", expireAfterSeconds=0
    )

    logger.info("Successfully connected to MongoDB.")


async def close_mongo_connection(app: FastAPI) -> None:
    """Close the MongoDB client during application shutdown."""
    client = getattr(app.state, "mongo_client", None)

    if client is not None:
        await client.close()
        app.state.mongo_client = None
        app.state.database = None
        logger.info("MongoDB connection closed.")
