"""MongoDB connection and lifecycle management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

from app.utils.config import settings

logger = logging.getLogger(__name__)

_mongo_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Initialize MongoDB connection and create indexes."""
    global _mongo_client, _db

    logger.info(f"Connecting to MongoDB: {settings.mongodb_uri[:50]}...")
    _mongo_client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
    )

    # Test connection
    try:
        await _mongo_client.admin.command("ping")
        logger.info("MongoDB connection successful")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

    _db = _mongo_client[settings.database_name]
    await _create_indexes()


async def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    global _mongo_client, _db

    if _mongo_client:
        logger.info("Closing MongoDB connection")
        _mongo_client.close()
        _mongo_client = None
        _db = None


async def _create_indexes() -> None:
    """Create necessary indexes for vector search."""
    if _db is None:
        raise RuntimeError("MongoDB not connected")

    # Documents collection indexes
    documents_col = _db[settings.documents_collection]
    await documents_col.create_index([("filename", ASCENDING)])
    await documents_col.create_index([("uploaded_at", DESCENDING)])
    logger.info("Created indexes on documents collection")

    # Chunks collection indexes
    chunks_col = _db[settings.chunks_collection]
    await chunks_col.create_index([("document_id", ASCENDING)])
    await chunks_col.create_index([("source", ASCENDING)])

    # Vector search index (requires MongoDB Atlas)
    try:
        vector_search_index = {
            "name": "vector_search_index",
            "type": "vectorSearch",
            "definition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": settings.embedding_dimension,
                        "similarity": "cosine",
                    }
                ]
            },
        }
        await chunks_col.create_search_index(vector_search_index)
        logger.info("Created vector search index on chunks collection")
    except OperationFailure as e:
        # Atlas returns code 68 when the search index name already exists.
        if getattr(e, "code", None) == 68 or "already defined" in str(e):
            logger.info("Vector search index already exists on chunks collection")
        else:
            logger.warning(f"Could not create vector search index: {e}")
    except Exception as e:
        logger.warning(f"Could not create vector search index: {e}")


def get_database() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    if _db is None:
        raise RuntimeError("MongoDB not initialized")
    return _db


def get_mongo_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance."""
    if _mongo_client is None:
        raise RuntimeError("MongoDB not initialized")
    return _mongo_client


@asynccontextmanager
async def get_db_session():
    """Context manager for database sessions."""
    db = get_database()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise
