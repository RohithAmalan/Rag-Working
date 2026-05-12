"""MongoDB Vector Search service."""

from __future__ import annotations

import logging
import re
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.collections import ChunksCollection, DocumentsCollection
from app.services.embedding_service import generate_batch_embeddings
from app.utils.config import settings

logger = logging.getLogger(__name__)


def _extract_exact_terms(query_text: str) -> list[str]:
    """Extract exact lookup terms like alphanumeric IDs and phone numbers."""
    terms: list[str] = []

    # Alphanumeric IDs should contain both letters and digits (avoid words like "customer").
    for token in re.findall(r"\b[0-9A-Za-z]{6,}\b", query_text):
        has_alpha = any(ch.isalpha() for ch in token)
        has_digit = any(ch.isdigit() for ch in token)
        if has_alpha and has_digit:
            terms.append(token)

    # Phone-like sequences with separators; keep raw term for exact regex.
    for token in re.findall(r"\+?\d[\d\-()\s]{6,}\d", query_text):
        terms.append(token.strip())

    # De-duplicate preserving order.
    seen: set[str] = set()
    unique_terms: list[str] = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique_terms.append(term)
    return unique_terms


class MongoVectorService:
    """Service for vector storage and retrieval using MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.documents = DocumentsCollection(db)
        self.chunks = ChunksCollection(db)

    async def store_document_chunks(
        self,
        filename: str,
        file_type: str,
        path: str,
        chunk_texts: list[str],
        chunk_metadata_list: list[dict[str, Any]] | None = None,
        source_priority: str = "primary",
    ) -> dict[str, Any]:
        """Store document and its chunks with embeddings.

        Args:
            filename: Name of uploaded file
            file_type: Type of file (pdf, csv, xlsx)
            path: Path to stored file
            chunk_texts: List of chunk texts to embed
            source_priority: Priority level (primary/secondary)

        Returns:
            Dictionary with insertion stats
        """
        logger.info(f"Storing document: {filename} with {len(chunk_texts)} chunks")

        # Insert document metadata
        document_id = await self.documents.insert_document(
            filename=filename,
            file_type=file_type,
            path=path,
        )

        # Generate embeddings for all chunks
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks")
        embeddings = generate_batch_embeddings(chunk_texts)

        # Prepare chunk documents with embeddings
        chunks_to_insert = []
        for idx, (text, emb) in enumerate(zip(chunk_texts, embeddings)):
            chunk_metadata = dict(chunk_metadata_list[idx]) if chunk_metadata_list and idx < len(chunk_metadata_list) else {}
            chunk_metadata.setdefault("file_name", filename)
            chunk_metadata.setdefault("source_type", file_type)
            chunk_metadata["file_type"] = file_type
            chunk_metadata.setdefault("source_priority", source_priority)

            chunks_to_insert.append(
                {
                    "chunk_text": text,
                    "embedding": emb,
                    "chunk_index": chunk_metadata.get("chunk_index", idx),
                    "source": filename,
                    "metadata": chunk_metadata,
                }
            )

        # Insert all chunks at once
        chunk_ids = await self.chunks.insert_chunks_batch(document_id, chunks_to_insert)

        logger.info(
            f"Successfully stored {len(chunk_ids)} chunks for document {document_id}"
        )

        return {
            "document_id": str(document_id),
            "filename": filename,
            "chunks_stored": len(chunk_ids),
            "total_chunks": len(chunk_texts),
        }

    async def search_chunks(
        self,
        query_text: str,
        top_k: int = 5,
        source_priority: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for relevant chunks using vector similarity.

        Args:
            query_text: User query or question
            top_k: Number of top chunks to return
            source_priority: Optional filter (primary/secondary)

        Returns:
            List of relevant chunks with similarity scores
        """
        logger.info(f"Searching for query: {query_text[:100]}... (top_k={top_k})")

        # 1) Exact lookup pass for IDs/phone numbers.
        exact_terms = _extract_exact_terms(query_text)
        if exact_terms:
            exact_hits: list[dict[str, Any]] = []
            for term in exact_terms:
                regex_filter: dict[str, Any] = {
                    "chunk_text": {"$regex": re.escape(term), "$options": "i"}
                }
                if source_priority:
                    regex_filter["metadata.source_priority"] = source_priority

                matches = await self.db[settings.chunks_collection].find(regex_filter).limit(top_k).to_list(length=top_k)
                for match in matches:
                    exact_hits.append(
                        {
                            "chunk_text": match.get("chunk_text", ""),
                            "source": match.get("source", "unknown"),
                            "document_id": str(match.get("document_id", "")),
                            "chunk_index": match.get("chunk_index", 0),
                            "similarity_score": 0.99,
                            "metadata": {
                                **match.get("metadata", {}),
                                "file_name": match.get("metadata", {}).get("file_name", match.get("source", "unknown")),
                                "source_type": match.get("metadata", {}).get(
                                    "source_type",
                                    match.get("metadata", {}).get("file_type", "unknown"),
                                ),
                            },
                        }
                    )

            # For numeric terms, also try separator-tolerant matching (e.g., 2290775154 vs 229-077-5154).
            for term in exact_terms:
                digits_only = re.sub(r"\D", "", term)
                if len(digits_only) < 7:
                    continue
                tolerant_pattern = "\\D*".join(re.escape(ch) for ch in digits_only)
                tolerant_filter: dict[str, Any] = {
                    "chunk_text": {"$regex": tolerant_pattern, "$options": "i"}
                }
                if source_priority:
                    tolerant_filter["metadata.source_priority"] = source_priority

                matches = await self.db[settings.chunks_collection].find(tolerant_filter).limit(top_k).to_list(length=top_k)
                for match in matches:
                    exact_hits.append(
                        {
                            "chunk_text": match.get("chunk_text", ""),
                            "source": match.get("source", "unknown"),
                            "document_id": str(match.get("document_id", "")),
                            "chunk_index": match.get("chunk_index", 0),
                            "similarity_score": 0.98,
                            "metadata": {
                                **match.get("metadata", {}),
                                "file_name": match.get("metadata", {}).get("file_name", match.get("source", "unknown")),
                                "source_type": match.get("metadata", {}).get(
                                    "source_type",
                                    match.get("metadata", {}).get("file_type", "unknown"),
                                ),
                            },
                        }
                    )

            # De-duplicate exact hits and return if present.
            if exact_hits:
                dedup: list[dict[str, Any]] = []
                seen_keys: set[tuple[str, int]] = set()
                for hit in exact_hits:
                    key = (hit.get("source", ""), int(hit.get("chunk_index", 0)))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        dedup.append(hit)
                logger.info(f"Found {len(dedup)} exact-match chunks")
                return dedup[:top_k]

        from app.services.embedding_service import generate_single_embedding

        # Generate query embedding
        query_embedding = generate_single_embedding(query_text)

        # Search using MongoDB vector search
        results = await self.chunks.vector_search(
            embedding=query_embedding,
            top_k=top_k,
            source_priority=source_priority,
        )

        logger.info(f"Found {len(results)} relevant chunks")

        # Return formatted results
        return [
            {
                "chunk_text": result.get("chunk_text", ""),
                "source": result.get("source", "unknown"),
                "document_id": str(result.get("document_id", "")),
                "chunk_index": result.get("chunk_index", 0),
                "similarity_score": result.get("similarity_score", 0.0),
                "metadata": {
                    **result.get("metadata", {}),
                    "file_name": result.get("metadata", {}).get("file_name", result.get("source", "unknown")),
                    "source_type": result.get("metadata", {}).get(
                        "source_type",
                        result.get("metadata", {}).get("file_type", "unknown"),
                    ),
                },
            }
            for result in results
        ]

    async def get_document_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Get document metadata by ID.

        Args:
            document_id: MongoDB ObjectId as string

        Returns:
            Document metadata or None
        """
        try:
            doc = await self.documents.get_document(ObjectId(document_id))
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None

    async def get_all_documents(self) -> list[dict[str, Any]]:
        """Get all stored documents.

        Returns:
            List of document metadata
        """
        docs = await self.documents.get_all_documents()
        return [
            {
                "_id": str(doc["_id"]),
                "filename": doc.get("filename", ""),
                "file_type": doc.get("file_type", ""),
                "path": doc.get("path", ""),
                "uploaded_at": doc.get("uploaded_at", None),
            }
            for doc in docs
        ]

    async def delete_document(self, document_id: str) -> dict[str, Any]:
        """Delete document and all its chunks.

        Args:
            document_id: MongoDB ObjectId as string

        Returns:
            Deletion stats
        """
        try:
            doc_id = ObjectId(document_id)

            # Delete document metadata
            docs_deleted = await self.documents.delete_document(doc_id)

            # Delete all chunks for this document
            chunks_deleted = await self.chunks.delete_chunks_by_document(doc_id)

            logger.info(f"Deleted document {document_id} and {chunks_deleted} chunks")

            return {
                "document_id": document_id,
                "documents_deleted": docs_deleted,
                "chunks_deleted": chunks_deleted,
            }
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return {
                "document_id": document_id,
                "error": str(e),
            }

    async def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics.

        Returns:
            Dictionary with store stats
        """
        total_documents = len(await self.documents.get_all_documents())
        total_chunks = await self.chunks.get_chunk_count()

        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "embedding_model": settings.embedding_model,
            "embedding_dimension": settings.embedding_dimension,
        }
