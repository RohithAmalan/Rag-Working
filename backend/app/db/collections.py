"""MongoDB collection schemas and operations."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.services.embedding_service import cosine_similarity
from app.utils.config import settings

logger = logging.getLogger(__name__)


class DocumentsCollection:
    """Document metadata collection manager."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection: AsyncIOMotorCollection = db[settings.documents_collection]

    async def insert_document(
        self,
        filename: str,
        file_type: str,
        path: str,
    ) -> ObjectId:
        """Insert document metadata."""
        doc = {
            "filename": filename,
            "file_type": file_type,
            "path": path,
            "uploaded_at": datetime.utcnow(),
        }
        result = await self.collection.insert_one(doc)
        return result.inserted_id

    async def get_document(self, document_id: ObjectId) -> dict[str, Any] | None:
        """Get document by ID."""
        return await self.collection.find_one({"_id": document_id})

    async def get_all_documents(self) -> list[dict[str, Any]]:
        """Get all documents."""
        cursor = self.collection.find()
        return await cursor.to_list(length=None)

    async def delete_document(self, document_id: ObjectId) -> int:
        """Delete document and return count."""
        result = await self.collection.delete_one({"_id": document_id})
        return result.deleted_count


class ChunksCollection:
    """Document chunks with embeddings collection manager."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection: AsyncIOMotorCollection = db[settings.chunks_collection]

    async def insert_chunk(
        self,
        document_id: ObjectId,
        chunk_text: str,
        embedding: list[float],
        chunk_index: int,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> ObjectId:
        """Insert chunk with embedding vector."""
        chunk = {
            "document_id": document_id,
            "chunk_text": chunk_text,
            "embedding": embedding,
            "chunk_index": chunk_index,
            "source": source,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
        }
        result = await self.collection.insert_one(chunk)
        return result.inserted_id

    async def insert_chunks_batch(
        self,
        document_id: ObjectId,
        chunks: list[dict[str, Any]],
    ) -> list[ObjectId]:
        """Insert multiple chunks at once."""
        chunk_docs = [
            {
                "document_id": document_id,
                "chunk_text": chunk["chunk_text"],
                "embedding": chunk["embedding"],
                "chunk_index": chunk.get("chunk_index", idx),
                "source": chunk.get("source", "unknown"),
                "metadata": chunk.get("metadata", {}),
                "created_at": datetime.utcnow(),
            }
            for idx, chunk in enumerate(chunks)
        ]
        result = await self.collection.insert_many(chunk_docs)
        return result.inserted_ids

    async def vector_search(
        self,
        embedding: list[float],
        top_k: int = 5,
        source_priority: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search chunks by vector similarity using MongoDB Atlas Vector Search."""
        match_stage = []
        if source_priority:
            match_stage.append({"$match": {"metadata.source_priority": source_priority}})

        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_search_index",
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": max(top_k * 20, 100),
                    "limit": top_k,
                }
            },
            *match_stage,
            {
                "$project": {
                    "chunk_text": 1,
                    "source": 1,
                    "document_id": 1,
                    "chunk_index": 1,
                    "metadata": 1,
                    "similarity_score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            cursor = self.collection.aggregate(pipeline)
            atlas_results = await cursor.to_list(length=None)
            if atlas_results:
                return atlas_results
            logger.warning("Atlas vector search returned no hits, falling back to manual cosine search")
        except Exception as exc:
            logger.warning(f"Atlas vector search failed, falling back to manual cosine search: {exc}")

        query: dict[str, Any] = {}
        if source_priority:
            query["metadata.source_priority"] = source_priority

        docs = await self.collection.find(
            query,
            {
                "chunk_text": 1,
                "source": 1,
                "document_id": 1,
                "chunk_index": 1,
                "metadata": 1,
                "embedding": 1,
            },
        ).to_list(length=None)

        scored = []
        for doc in docs:
            doc_embedding = doc.get("embedding")
            if not doc_embedding:
                continue
            score = cosine_similarity(embedding, doc_embedding)
            doc["similarity_score"] = score
            scored.append(doc)

        scored.sort(key=lambda item: item.get("similarity_score", 0.0), reverse=True)
        return scored[:top_k]

    async def get_chunks_by_document(
        self, document_id: ObjectId
    ) -> list[dict[str, Any]]:
        """Get all chunks for a document."""
        cursor = self.collection.find({"document_id": document_id}).sort(
            "chunk_index", 1
        )
        return await cursor.to_list(length=None)

    async def delete_chunks_by_document(self, document_id: ObjectId) -> int:
        """Delete all chunks for a document."""
        result = await self.collection.delete_many({"document_id": document_id})
        return result.deleted_count

    async def get_chunk_count(self) -> int:
        """Get total chunk count."""
        return await self.collection.count_documents({})
