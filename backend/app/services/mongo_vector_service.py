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
        "full_names": [],
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

    # Pattern 2: Hyphenated / prefixed IDs like ORD-10028, C-5076, REG-100138, INV-001
    for token in re.findall(r"\b[A-Za-z]{1,10}[-'][0-9]{2,}\b", query_text):
        result["ids"].append(token)

    # Pattern 3: IDs with special characters like REG'100138 (no hyphen pattern above)
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

    # Extract full names first (e.g., "Donna Harris") to avoid broad single-name mismatches.
    for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b", query_text):
        phrase = match.group(1).strip()
        phrase_l = phrase.lower()
        if any(noise in phrase_l for noise in ["file", "report", "sheet", "table", "orders", "order", "details"]):
            continue
        result["full_names"].append(phrase)

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


def _normalized_original_file_name(stored_file_name: str) -> str:
    """Normalize stored file name by stripping UUID prefix if present."""
    name = str(stored_file_name or "").strip()
    # Stored names are typically: <uuid>_<original-name>
    if "_" in name and len(name.split("_", 1)[0]) >= 16:
        return name.split("_", 1)[1].lower()
    return name.lower()


def _matches_required_file(metadata: dict[str, Any], required_file_name: str | None) -> bool:
    if not required_file_name:
        return True
    stored = str(metadata.get("file_name", ""))
    normalized_required = required_file_name.lower().strip()
    normalized_stored_original = _normalized_original_file_name(stored)
    return normalized_required == normalized_stored_original


def _extract_numeric_from_chunk(chunk_text: str, field_name: str) -> float | None:
    pattern = rf"{re.escape(field_name)}\s+is\s+([-+]?\d*\.?\d+)"
    match = re.search(pattern, chunk_text, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_numeric_facts(chunk_text: str) -> dict[str, float]:
    """Extract numeric facts from patterns like '<Field> is <number>'."""
    facts: dict[str, float] = {}
    for raw_key, raw_value in re.findall(r"([A-Za-z][A-Za-z0-9_ /()\-]{1,50})\s+is\s+([-+]?\d*\.?\d+)", chunk_text):
        key = re.sub(r"\s+", " ", raw_key).strip()
        if not key:
            continue
        try:
            facts[key] = float(raw_value)
        except ValueError:
            continue
    return facts


def _normalize_metric_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _choose_metric_key(query_text: str, numeric_facts: dict[str, float]) -> str | None:
    if not numeric_facts:
        return None

    q_lower = query_text.lower()
    q_tokens = {
        token
        for token in re.findall(r"[a-z]+", q_lower)
        if token not in {"top", "highest", "lowest", "max", "min", "minimum", "list", "show", "get", "with", "their", "the"}
    }

    best_key: str | None = None
    best_score = -1
    for key in numeric_facts.keys():
        key_tokens = set(re.findall(r"[a-z]+", key.lower()))
        overlap_score = len(q_tokens & key_tokens)
        if overlap_score > best_score:
            best_score = overlap_score
            best_key = key

    if best_key and best_score > 0:
        return best_key

    # Fallbacks for common metric-oriented intents.
    if "price" in q_lower:
        for key in numeric_facts.keys():
            if "price" in key.lower():
                return key
    if "sales" in q_lower:
        for key in numeric_facts.keys():
            if "sales" in key.lower():
                return key
    if "quantity" in q_lower:
        for key in numeric_facts.keys():
            if "quantity" in key.lower() or "qty" in key.lower():
                return key

    return best_key


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
        required_file_name: str | None = None,
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
        has_full_names = bool(exact_terms["full_names"])
        has_names = bool(exact_terms["names"])
        # If UI already selected a specific file, ignore file hints from question text
        # to avoid conflicts from misspellings/variants in natural language.
        if required_file_name:
            exact_terms["file_hints"] = []
        file_hint_filter = _build_file_hint_filter(exact_terms["file_hints"])
        required_file_filter = None
        if required_file_name:
            escaped = re.escape(required_file_name)
            # Match exact original file name, optionally with UUID prefix.
            required_file_filter = {
                "metadata.file_name": {
                    "$regex": rf"(?:^|^[0-9a-f]{{16,}}_){escaped}$",
                    "$options": "i",
                }
            }

        exact_hits: list[dict[str, Any]] = []

        logger.debug(f"Query analysis: ids={len(exact_terms['ids'])}, phones={len(exact_terms['phones'])}, names={len(exact_terms['names'])}")

        # ============ FAST PATH: aggregate computation (avg / sum / count) ============
        q_lower = query_text.lower()
        _AGG_KEYWORDS: dict[str, str] = {
            "average": "avg", "avg": "avg", "mean": "avg",
            "total": "sum", "sum": "sum",
            "how many": "count", "number of": "count", "count": "count",
        }
        asks_aggregate: str | None = None
        for kw, agg_type in _AGG_KEYWORDS.items():
            if kw in q_lower:
                asks_aggregate = agg_type
                break

        # Only run aggregate path when a file scope is known (required_file_name or file hint)
        if asks_aggregate and (required_file_name or file_hint_filter):
            agg_clauses: list[dict[str, Any]] = []
            if required_file_filter:
                agg_clauses.append(required_file_filter)
            elif file_hint_filter:
                agg_clauses.append(file_hint_filter)
            if source_priority:
                agg_clauses.append({"metadata.source_priority": source_priority})

            agg_filter = {"$and": agg_clauses} if len(agg_clauses) > 1 else (agg_clauses[0] if agg_clauses else {})
            all_agg_chunks = await self.db[settings.chunks_collection].find(agg_filter).to_list(length=None)
            logger.info(f"Aggregate fast path: fetched {len(all_agg_chunks)} chunks for '{asks_aggregate}' query")

            key_votes: dict[str, int] = {}
            cached_facts: list[tuple[dict[str, Any], dict[str, float]]] = []
            for row in all_agg_chunks:
                facts = _extract_numeric_facts(str(row.get("chunk_text", "")))
                if not facts:
                    continue
                cached_facts.append((row, facts))
                chosen = _choose_metric_key(query_text, facts)
                if chosen:
                    norm = _normalize_metric_key(chosen)
                    key_votes[norm] = key_votes.get(norm, 0) + 1

            if cached_facts and key_votes:
                best_key_norm = max(key_votes, key=lambda k: key_votes[k])

                # Collect all values for the winning metric
                values: list[float] = []
                display_field_name = best_key_norm  # fallback
                for row, facts in cached_facts:
                    for key, value in facts.items():
                        if _normalize_metric_key(key) == best_key_norm:
                            if display_field_name == best_key_norm:
                                display_field_name = key.title()
                            values.append(value)
                            break

                if values:
                    if asks_aggregate == "avg":
                        result_val = sum(values) / len(values)
                        agg_label = "Average"
                    elif asks_aggregate == "sum":
                        result_val = sum(values)
                        agg_label = "Total"
                    else:  # count
                        result_val = float(len(values))
                        agg_label = "Count"

                    synthetic = (
                        f"Computed result: {agg_label} {display_field_name} = {result_val:.2f} "
                        f"(based on {len(values)} records)"
                    )
                    logger.info(f"Aggregate result: {synthetic}")
                    return [
                        {
                            "chunk_text": synthetic,
                            "source": required_file_name or "aggregate",
                            "document_id": "",
                            "chunk_index": 0,
                            "similarity_score": 1.0,
                            "metadata": {
                                "source_type": "excel",
                                "source_priority": "primary",
                                "file_name": required_file_name or "",
                            },
                        }
                    ]

        # ============ FAST PATH: numeric metric ranking in selected file ============
        asks_metric_rank = any(token in q_lower for token in ["price", "sales", "quantity", "amount", "cost", "revenue", "score", "value", "profit", "discount"]) and any(
            token in q_lower for token in ["highest", "max", "top", "lowest", "minimum", "min"]
        )
        if required_file_name and asks_metric_rank:
            top_match = re.search(r"\btop\s+(\d+)\b", q_lower)
            n = int(top_match.group(1)) if top_match else top_k
            n = max(1, min(n, 20))

            rank_clauses: list[dict[str, Any]] = [required_file_filter] if required_file_filter else []
            if source_priority:
                rank_clauses.append({"metadata.source_priority": source_priority})

            rank_filter = {"$and": rank_clauses} if len(rank_clauses) > 1 else (rank_clauses[0] if rank_clauses else {})
            candidates = await self.db[settings.chunks_collection].find(rank_filter).limit(5000).to_list(length=5000)

            key_votes: dict[str, int] = {}
            cached_facts: list[tuple[dict[str, Any], dict[str, float]]] = []
            for row in candidates:
                facts = _extract_numeric_facts(str(row.get("chunk_text", "")))
                if not facts:
                    continue
                cached_facts.append((row, facts))
                chosen = _choose_metric_key(query_text, facts)
                if chosen:
                    norm = _normalize_metric_key(chosen)
                    key_votes[norm] = key_votes.get(norm, 0) + 1

            chosen_metric_norm = max(key_votes.items(), key=lambda kv: kv[1])[0] if key_votes else None
            scored_rows: list[tuple[float, dict[str, Any]]] = []
            for row, facts in cached_facts:
                metric_value: float | None = None
                if chosen_metric_norm:
                    for key, value in facts.items():
                        if _normalize_metric_key(key) == chosen_metric_norm:
                            metric_value = value
                            break
                if metric_value is None:
                    fallback_key = _choose_metric_key(query_text, facts)
                    if fallback_key:
                        metric_value = facts.get(fallback_key)
                if metric_value is None:
                    continue
                scored_rows.append((metric_value, row))

            if scored_rows:
                wants_lowest = any(token in q_lower for token in ["lowest", "minimum", "min"])
                scored_rows.sort(key=lambda item: item[0], reverse=not wants_lowest)
                picked = [row for _, row in scored_rows[:n]]

                return [
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
                    for match in picked
                ]

        # ============ STRATEGY 1: EMAILS (Most specific for person lookup) ============
        if has_emails:
            logger.debug("Strategy 1: Exact email search")
            for email in exact_terms["emails"]:
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": re.escape(email), "$options": "i"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if required_file_filter:
                    query_clauses.append(required_file_filter)
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

        # ============ STRATEGY 2: FULL NAMES (high precision) ============
        if has_full_names and not exact_hits:
            logger.debug("Strategy 2: Exact full-name search")
            for full_name in exact_terms["full_names"]:
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": re.escape(full_name), "$options": "i"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if required_file_filter:
                    query_clauses.append(required_file_filter)
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
                        "similarity_score": 0.995,
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

        # ============ STRATEGY 3: NAMES + PHONES (Most specific) ============
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
                    if required_file_filter:
                        query_clauses.append(required_file_filter)
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

        # ============ STRATEGY 4: NAMES ONLY ============
        if has_names and not exact_hits:
            logger.debug("Strategy 4: Name search only")
            for name in exact_terms["names"]:
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": f"(?i).*{re.escape(name)}.*"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if required_file_filter:
                    query_clauses.append(required_file_filter)
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

        # ============ STRATEGY 5: IDS ============
        if has_ids and not exact_hits:
            logger.debug("Strategy 5: ID search")
            for term_id in exact_terms["ids"]:
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": re.escape(term_id), "$options": "i"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if required_file_filter:
                    query_clauses.append(required_file_filter)
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

        # ============ STRATEGY 6: PHONES (Most lenient) ============
        if has_phones and not exact_hits:
            logger.debug("Strategy 6: Phone search with tolerance")
            for phone in exact_terms["phones"]:
                # Try exact match first
                query_clauses: list[dict[str, Any]] = [
                    {"chunk_text": {"$regex": re.escape(phone), "$options": "i"}},
                ]
                if file_hint_filter:
                    query_clauses.append(file_hint_filter)
                if required_file_filter:
                    query_clauses.append(required_file_filter)
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
                        if required_file_filter:
                            tolerant_clauses.append(required_file_filter)
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

        if required_file_name:
            results = [
                result
                for result in results
                if _matches_required_file(result.get("metadata", {}), required_file_name)
            ]

        # Handle file hint filtering with fallback if no matches
        if exact_terms["file_hints"]:
            file_filtered_results = [
                result for result in results
                if _matches_file_hints(result.get("metadata", {}), exact_terms["file_hints"])
            ]
            
            # If semantic search found results but file hints filtered them all out,
            # it means user mentioned a file that doesn't exist - ask them which one they meant
            if results and not file_filtered_results and not required_file_name:
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
            if _matches_required_file(result.get("metadata", {}), required_file_name)
        ]

    async def delete_document_and_chunks(self, document_id: str) -> int:
        """Delete a document and all linked chunks."""
        obj_id = ObjectId(document_id)
        deleted_chunks = await self.chunks.delete_chunks_by_document(obj_id)
        await self.documents.delete_document(obj_id)
        return deleted_chunks

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

    async def get_documents_by_filename(self, filename: str) -> list[dict[str, Any]]:
        """Get all stored documents by original filename."""
        try:
            cursor = self.documents.collection.find({"filename": filename})
            docs = await cursor.to_list(length=None)
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
            logger.error(f"Error retrieving documents by filename: {e}")
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
