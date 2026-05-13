"""MongoDB Vector Search service - IMPROVED HYBRID SEARCH."""

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


def _extract_exact_terms(query_text: str) -> dict[str, list[str]]:
    """Extract exact lookup terms: IDs, phones, and names."""
    result = {
        "ids": [],
        "phones": [],
        "emails": [],
        "names": [],
        "file_hints": [],
    }

    # Extract alphanumeric IDs (including those with special chars like REG'100138)
    # Pattern 1: Normal IDs (6+ chars, mix of letters/numbers)
    for token in re.findall(r"\b[0-9A-Za-z]{6,}\b", query_text):
        has_alpha = any(ch.isalpha() for ch in token)
        has_digit = any(ch.isdigit() for ch in token)
        if has_alpha and has_digit:
            result["ids"].append(token)
    
    # Pattern 2: IDs with special characters like REG'100138 or REG-100138
    for token in re.findall(r"\b[A-Za-z]+['\-]?[0-9]{6,}\b", query_text):
        # Clean punctuation from the ID
        cleaned_id = re.sub(r"['\-_]", "", token)
        result["ids"].append(cleaned_id)

    # Extract phone-like sequences with separators
    for token in re.findall(r"\+?\d[\d\-()\s.x]{6,}\d", query_text):
        result["phones"].append(token.strip())

    # Extract emails
    for token in re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", query_text):
        result["emails"].append(token.strip())

    # Extract names (capitalized words, length 2-20)
    for token in re.findall(r"\b[A-Z][a-z]+\b", query_text):
        if 2 <= len(token) <= 20:
            result["names"].append(token)

    # Extract explicit file names and common base-name hints.
    for token in re.findall(r"\b[\w-]+\.(?:csv|xlsx|pdf)\b", query_text, re.IGNORECASE):
        result["file_hints"].append(token.strip())
    
    # Extract specific file name patterns (hyphenated versions)
    for token in re.findall(r"\b(?:people-\d+|customers-\d+|product-sales-region)\b", query_text, re.IGNORECASE):
        result["file_hints"].append(token.strip())
    
    # Natural language file references - match descriptive phrases like "product sales region file", "sales report"
    # This captures patterns like: [word word word] + (file|report|sheet|data)
    for match in re.finditer(r"\b(?:product\s+sales(?:\s+region)?|sales\s+region|customers|people|projects?|product|order|inventory)\s+(?:file|report|sheet|data|table)\b", query_text, re.IGNORECASE):
        file_hint = match.group(0).strip()
        # Normalize to match our filenames
        if "product" in file_hint.lower() and "sales" in file_hint.lower():
            result["file_hints"].append("product-sales-region")
        elif "customer" in file_hint.lower():
            result["file_hints"].append("customers")
        elif "people" in file_hint.lower():
            result["file_hints"].append("people")
        elif "project" in file_hint.lower():
            result["file_hints"].append("project")

    # De-duplicate each category
    for key in result:
        seen: set[str] = set()
        unique: list[str] = []
        for term in result[key]:
            term_key = term.lower()
            if term_key not in seen:
                seen.add(term_key)
                unique.append(term)
        result[key] = unique

    return result


def _build_file_hint_filter(file_hints: list[str]) -> dict[str, Any] | None:
    if not file_hints:
        return None

    # Build flexible matching patterns that handle various naming conventions
    or_clauses = []
    for file_hint in file_hints:
        # Normalize the hint for matching
        normalized = file_hint.lower().replace("-", "").replace("_", "").replace(" ", "")
        
        # Create multiple regex patterns to match different naming conventions
        or_clauses.append({"metadata.file_name": {"$regex": re.escape(file_hint), "$options": "i"}})
        
        # Also try without separators for more flexible matching
        if normalized:
            or_clauses.append({
                "metadata.file_name": {"$regex": normalized.replace(" ", ".*"), "$options": "i"}
            })
    
    return {"$or": or_clauses} if or_clauses else None


def _matches_file_hints(metadata: dict[str, Any], file_hints: list[str]) -> bool:
    if not file_hints:
        return True

    file_name = str(metadata.get("file_name", "")).lower()
    normalized_filename = file_name.replace("-", "").replace("_", "").replace(" ", "")
    
    for file_hint in file_hints:
        # Direct substring match (case-insensitive)
        if file_hint.lower() in file_name:
            return True
        # Normalized match (without separators)
        normalized_hint = file_hint.lower().replace("-", "").replace("_", "").replace(" ", "")
        if normalized_hint in normalized_filename:
            return True
    
    return False


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
        document_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store document and its chunks with embeddings."""
        logger.info(f"Storing document: {filename} with {len(chunk_texts)} chunks")

        # Insert document metadata
        document_id = await self.documents.insert_document(
            filename=filename,
            file_type=file_type,
            path=path,
            metadata=document_metadata,
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

        logger.info(f"Successfully stored {len(chunk_ids)} chunks for document {document_id}")

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
        """
        Intelligent hybrid search supporting:
        - Name + Phone: "Louis Payne's mobile number" → returns Louis's phone
        - Name only: "Virginia" → returns all Virginia records
        - Phone only: "027-846-3705x14184" → returns matching phone record
        - ID only: "8C2811a503C7c5a" → returns exact ID record
        - General query: falls back to semantic search
        """
        logger.info(f"Searching for query: {query_text[:100]}... (top_k={top_k})")

        # Extract all search terms
        exact_terms = _extract_exact_terms(query_text)
        has_ids = bool(exact_terms["ids"])
        has_phones = bool(exact_terms["phones"])
        has_emails = bool(exact_terms["emails"])
        has_names = bool(exact_terms["names"])
        file_hint_filter = _build_file_hint_filter(exact_terms["file_hints"])

        exact_hits: list[dict[str, Any]] = []

        logger.debug(f"Query analysis: ids={len(exact_terms['ids'])}, phones={len(exact_terms['phones'])}, names={len(exact_terms['names'])}")

        # ============ STRATEGY 1: EMAILS (Most specific for person lookup) ============
        if has_emails:
            logger.debug("Strategy 1: Exact email search")
            for email in exact_terms["emails"]:
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": re.escape(email), "$options": "i"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if source_priority:
                    query_clauses.append({"metadata.source_priority": source_priority})

                query_filter = {"$and": query_clauses} if len(query_clauses) > 1 else query_clauses[0]
                matches = await self.db[settings.chunks_collection].find(query_filter).limit(top_k).to_list(length=top_k)

                for match in matches:
                    exact_hits.append({
                        "chunk_text": match.get("chunk_text", ""),
                        "source": match.get("source", "unknown"),
                        "document_id": str(match.get("document_id", "")),
                        "chunk_index": match.get("chunk_index", 0),
                        "similarity_score": 1.0,
                        "metadata": {
                            **match.get("metadata", {}),
                            "file_name": match.get("metadata", {}).get("file_name", match.get("source", "unknown")),
                            "source_type": match.get("metadata", {}).get(
                                "source_type",
                                match.get("metadata", {}).get("file_type", "unknown"),
                            ),
                        },
                    })

                if exact_hits:
                    break

        # ============ STRATEGY 2: NAMES + PHONES (Most specific) ============
        if has_names and has_phones:
            logger.debug(f"Strategy 2: Multi-term search (name+phone)")
            for name in exact_terms["names"]:
                for phone in exact_terms["phones"]:
                    # Find records containing BOTH name and phone
                    query_clauses: list[dict[str, Any]] = [
                        {"chunk_text": {"$regex": f"(?i).*{re.escape(name)}.*"}},
                        {"chunk_text": {"$regex": re.escape(phone), "$options": "i"}},
                    ]
                    if file_hint_filter:
                        query_clauses.append(file_hint_filter)
                    if source_priority:
                        query_clauses.append({"metadata.source_priority": source_priority})

                    query_filter = {"$and": query_clauses}

                    matches = await self.db[settings.chunks_collection].find(query_filter).limit(top_k).to_list(length=top_k)
                    logger.debug(f"Found {len(matches)} records with {name}+{phone}")

                    for match in matches:
                        exact_hits.append({
                            "chunk_text": match.get("chunk_text", ""),
                            "source": match.get("source", "unknown"),
                            "document_id": str(match.get("document_id", "")),
                            "chunk_index": match.get("chunk_index", 0),
                            "similarity_score": 0.99,  # Highest confidence
                            "metadata": {
                                **match.get("metadata", {}),
                                "file_name": match.get("metadata", {}).get("file_name", match.get("source", "unknown")),
                                "source_type": match.get("metadata", {}).get(
                                    "source_type",
                                    match.get("metadata", {}).get("file_type", "unknown"),
                                ),
                            },
                        })

                    if exact_hits:
                        break
                if exact_hits:
                    break

        # ============ STRATEGY 3: NAMES ONLY ============
        if has_names and not exact_hits:
            logger.debug(f"Strategy 3: Name search only")
            for name in exact_terms["names"]:
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": f"(?i).*{re.escape(name)}.*"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if source_priority:
                    query_clauses.append({"metadata.source_priority": source_priority})

                query_filter = {"$and": query_clauses} if len(query_clauses) > 1 else query_clauses[0]

                matches = await self.db[settings.chunks_collection].find(query_filter).limit(top_k).to_list(length=top_k)
                logger.debug(f"Found {len(matches)} records with name {name}")

                for match in matches:
                    exact_hits.append({
                        "chunk_text": match.get("chunk_text", ""),
                        "source": match.get("source", "unknown"),
                        "document_id": str(match.get("document_id", "")),
                        "chunk_index": match.get("chunk_index", 0),
                        "similarity_score": 0.95,
                        "metadata": {
                            **match.get("metadata", {}),
                            "file_name": match.get("metadata", {}).get("file_name", match.get("source", "unknown")),
                            "source_type": match.get("metadata", {}).get(
                                "source_type",
                                match.get("metadata", {}).get("file_type", "unknown"),
                            ),
                        },
                    })

                if exact_hits:
                    break

        # ============ STRATEGY 4: IDS ============
        if has_ids and not exact_hits:
            logger.debug(f"Strategy 4: ID search")
            for term_id in exact_terms["ids"]:
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": re.escape(term_id), "$options": "i"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if source_priority:
                    query_clauses.append({"metadata.source_priority": source_priority})

                query_filter = {"$and": query_clauses} if len(query_clauses) > 1 else query_clauses[0]

                matches = await self.db[settings.chunks_collection].find(query_filter).limit(top_k).to_list(length=top_k)
                logger.debug(f"Found {len(matches)} records with ID {term_id}")

                for match in matches:
                    exact_hits.append({
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
                    })

                if exact_hits:
                    break

        # ============ STRATEGY 5: PHONES (Most lenient) ============
        if has_phones and not exact_hits:
            logger.debug(f"Strategy 5: Phone search with tolerance")
            for phone in exact_terms["phones"]:
                # Try exact match first
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": re.escape(phone), "$options": "i"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if source_priority:
                    query_clauses.append({"metadata.source_priority": source_priority})

                query_filter = {"$and": query_clauses} if len(query_clauses) > 1 else query_clauses[0]

                matches = await self.db[settings.chunks_collection].find(query_filter).limit(top_k).to_list(length=top_k)
                logger.debug(f"Found {len(matches)} records with exact phone {phone}")

                for match in matches:
                    exact_hits.append({
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
                    })

                # Separator-tolerant matching if no exact matches
                if not matches:
                    digits_only = re.sub(r"\D", "", phone)
                    if len(digits_only) >= 7:
                        tolerant_pattern = "\\D*".join(re.escape(ch) for ch in digits_only)
                        tolerant_clauses: list[dict[str, Any]] = [
                            {"chunk_text": {"$regex": tolerant_pattern, "$options": "i"}},
                        ]
                        if file_hint_filter:
                            tolerant_clauses.append(file_hint_filter)
                        if source_priority:
                            tolerant_clauses.append({"metadata.source_priority": source_priority})

                        tolerant_filter = {"$and": tolerant_clauses} if len(tolerant_clauses) > 1 else tolerant_clauses[0]

                        matches = await self.db[settings.chunks_collection].find(tolerant_filter).limit(top_k).to_list(length=top_k)
                        logger.debug(f"Found {len(matches)} records with tolerant phone match")

                        for match in matches:
                            exact_hits.append({
                                "chunk_text": match.get("chunk_text", ""),
                                "source": match.get("source", "unknown"),
                                "document_id": str(match.get("document_id", "")),
                                "chunk_index": match.get("chunk_index", 0),
                                "similarity_score": 0.97,
                                "metadata": {
                                    **match.get("metadata", {}),
                                    "file_name": match.get("metadata", {}).get("file_name", match.get("source", "unknown")),
                                    "source_type": match.get("metadata", {}).get(
                                        "source_type",
                                        match.get("metadata", {}).get("file_type", "unknown"),
                                    ),
                                },
                            })

                if exact_hits:
                    break

        # ============ DEDUP AND RETURN EXACT MATCHES ============
        if exact_hits:
            dedup: list[dict[str, Any]] = []
            seen_keys: set[tuple[str, int]] = set()
            for hit in exact_hits:
                key = (hit.get("source", ""), int(hit.get("chunk_index", 0)))
                if key not in seen_keys:
                    seen_keys.add(key)
                    dedup.append(hit)
            logger.info(f"Found {len(dedup)} exact-match chunks using hybrid search")
            return dedup[:top_k]

        # ============ FALLBACK: SEMANTIC SEARCH ============
        logger.debug("No exact matches, falling back to semantic vector search")
        from app.services.embedding_service import generate_single_embedding

        query_embedding = generate_single_embedding(query_text)

        results = await self.chunks.vector_search(
            embedding=query_embedding,
            top_k=max(top_k * 10, 20),
            source_priority=source_priority,
        )

        # Handle file hint filtering with fallback if no matches
        if exact_terms["file_hints"]:
            file_filtered_results = [
                result for result in results
                if _matches_file_hints(result.get("metadata", {}), exact_terms["file_hints"])
            ]
            
            # If semantic search found results but file hints filtered them all out,
            # it means user mentioned a file that doesn't exist - ask them which one they meant
            if results and not file_filtered_results:
                logger.warning(f"File hints {exact_terms['file_hints']} didn't match any results. Fetching available files.")
                available_files = await self.db[settings.chunks_collection].distinct("metadata.file_name")
                available_files = [f for f in available_files if f and f != "unknown"]
                
                error_msg = (
                    f"I couldn't find a file matching '{', '.join(exact_terms['file_hints'])}'. "
                    f"Available files are: {', '.join(available_files)}. "
                    f"Which file did you mean to search in?"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            if file_filtered_results:
                results = file_filtered_results

        logger.info(f"Semantic search found {len(results)} relevant chunks")

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
            for result in results[:top_k]
        ]

    async def get_document_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Get document metadata by ID."""
        try:
            doc = await self.documents.get_document(ObjectId(document_id))
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None

    async def get_all_documents(self) -> list[dict[str, Any]]:
        """Get all stored documents with metadata from documents collection."""
        try:
            docs = await self.documents.get_all_documents()
            return [
                {
                    "_id": str(doc.get("_id", "")),
                    "filename": doc.get("filename", ""),
                    "file_type": doc.get("file_type", "unknown"),
                    "path": doc.get("path", ""),
                    "metadata": doc.get("metadata", {}),
                    "uploaded_at": doc.get("uploaded_at"),
                }
                for doc in docs
            ]
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    async def get_vector_store_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        chunks_collection = self.db[settings.chunks_collection]
        total_chunks = await chunks_collection.count_documents({})
        primary = await chunks_collection.count_documents({"metadata.source_priority": "primary"})
        secondary = await chunks_collection.count_documents({"metadata.source_priority": "secondary"})
        unique_files = await chunks_collection.distinct("metadata.file_name")

        return {
            "total_chunks": total_chunks,
            "total_documents": len(unique_files),
            "primary_chunks": primary,
            "secondary_chunks": secondary,
            "backend": "mongodb",
        }
