"""Semantic caching service using Redis and vector similarity.

This service caches RAG query results in Redis. Before calling the expensive
LLM pipeline, each new query is embedded and compared (cosine similarity)
against previously cached query embeddings. If a similar-enough question was
already answered, the cached result is returned instantly.

Cache key layout in Redis:
  - rag:cache:embeddings   – Redis hash: { cache_id → JSON embedding list }
  - rag:cache:queries      – Redis hash: { cache_id → JSON query metadata }
  - rag:cache:results      – Redis hash: { cache_id → JSON result payload }
  - rag:cache:stats        – Redis hash: hits / misses / total
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Redis key namespaces
_NS_EMBEDDINGS = "rag:cache:embeddings"
_NS_QUERIES = "rag:cache:queries"
_NS_RESULTS = "rag:cache:results"
_NS_STATS = "rag:cache:stats"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Fast cosine similarity between two equal-length vectors."""
    arr_a = np.array(a, dtype=np.float32)
    arr_b = np.array(b, dtype=np.float32)
    dot = np.dot(arr_a, arr_b)
    norm = np.linalg.norm(arr_a) * np.linalg.norm(arr_b)
    return float(dot / norm) if norm > 1e-10 else 0.0


class SemanticCacheService:
    """Semantic cache for RAG queries backed by Redis.

    Usage::
        cache = SemanticCacheService(redis_client, similarity_threshold=0.92)
        await cache.initialize()

        result = await cache.get(question, selected_file)
        if result:
            return result   # cache hit

        # … run RAG pipeline …

        await cache.set(question, selected_file, rag_result)
    """

    def __init__(
        self,
        redis_client,
        similarity_threshold: float = 0.92,
        ttl_seconds: int = 3600,
    ) -> None:
        self._redis = redis_client
        self._threshold = similarity_threshold
        self._ttl = ttl_seconds
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Ping Redis to verify connectivity."""
        try:
            await self._redis.ping()
            self._initialized = True
            logger.info(
                f"SemanticCacheService ready (threshold={self._threshold}, "
                f"ttl={self._ttl}s)"
            )
        except Exception as exc:
            logger.warning(f"Redis ping failed – cache disabled: {exc}")
            self._initialized = False

    async def close(self) -> None:
        """Close the underlying Redis connection."""
        try:
            await self._redis.aclose()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(
        self,
        question: str,
        selected_file: str | None = None,
    ) -> dict[str, Any] | None:
        """Return a cached result if a semantically similar query exists.

        Returns ``None`` on a cache miss (or if Redis is unavailable).
        """
        if not self._initialized:
            return None

        try:
            query_embedding = await self._embed(question)
            best_id, best_score = await self._find_best_match(
                query_embedding, selected_file
            )

            if best_id and best_score >= self._threshold:
                result = await self._load_result(best_id)
                if result:
                    await self._incr_stat("hits")
                    logger.info(
                        f"Cache HIT (score={best_score:.3f}) for: "
                        f"{question[:60]}…"
                    )
                    result["_cache"] = {
                        "hit": True,
                        "similarity": round(best_score, 4),
                    }
                    return result

            await self._incr_stat("misses")
            logger.debug(f"Cache MISS for: {question[:60]}…")
            return None

        except Exception as exc:
            logger.warning(f"Cache lookup error (skipping): {exc}")
            return None

    async def set(
        self,
        question: str,
        selected_file: str | None,
        result: dict[str, Any],
    ) -> None:
        """Store a query/result pair in the cache."""
        if not self._initialized:
            return

        try:
            cache_id = str(uuid.uuid4())
            query_embedding = await self._embed(question)

            pipe = self._redis.pipeline()

            # Store embedding
            pipe.hset(_NS_EMBEDDINGS, cache_id, json.dumps(query_embedding))

            # Store query metadata
            meta = {
                "question": question,
                "selected_file": selected_file or "__all__",
                "cached_at": time.time(),
            }
            pipe.hset(_NS_QUERIES, cache_id, json.dumps(meta))

            # Store result (strip internal _cache key if present)
            clean_result = {k: v for k, v in result.items() if k != "_cache"}
            pipe.hset(_NS_RESULTS, cache_id, json.dumps(clean_result))

            await pipe.execute()

            # Set TTL on individual fields via EXPIRE on the keys
            # (Redis hashes don't support per-field TTL, so we rely on a
            #  separate expiry hash entry approach or just accept that entries
            #  accumulate. For simplicity we skip per-entry TTL here.)
            await self._incr_stat("total")

            logger.info(
                f"Cache SET [{cache_id[:8]}] for: {question[:60]}…"
            )

        except Exception as exc:
            logger.warning(f"Cache store error (skipping): {exc}")

    async def invalidate_all(self) -> int:
        """Clear every cache entry. Returns number of keys deleted."""
        if not self._initialized:
            return 0
        try:
            keys = [_NS_EMBEDDINGS, _NS_QUERIES, _NS_RESULTS, _NS_STATS]
            deleted = await self._redis.delete(*keys)
            logger.info(f"Cache invalidated ({deleted} keys removed)")
            return deleted
        except Exception as exc:
            logger.warning(f"Cache invalidation error: {exc}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """Return hit/miss/total counters and entry count."""
        if not self._initialized:
            return {"enabled": False}
        try:
            stats_raw = await self._redis.hgetall(_NS_STATS)
            entry_count = await self._redis.hlen(_NS_EMBEDDINGS)
            stats = {k.decode(): int(v) for k, v in stats_raw.items()}
            hits = stats.get("hits", 0)
            total = stats.get("hits", 0) + stats.get("misses", 0)
            return {
                "enabled": True,
                "entries": entry_count,
                "hits": hits,
                "misses": stats.get("misses", 0),
                "total_queries": stats.get("total", 0),
                "hit_rate": round(hits / total, 4) if total else 0.0,
                "threshold": self._threshold,
                "ttl_seconds": self._ttl,
            }
        except Exception as exc:
            logger.warning(f"Could not fetch cache stats: {exc}")
            return {"enabled": True, "error": str(exc)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _embed(self, text: str) -> list[float]:
        """Generate embedding in a thread pool to avoid blocking the event loop."""
        from app.services.embedding_service import generate_single_embedding

        return await asyncio.to_thread(generate_single_embedding, text)

    async def _find_best_match(
        self,
        query_embedding: list[float],
        selected_file: str | None,
    ) -> tuple[str | None, float]:
        """Scan all cached embeddings and return (cache_id, best_similarity)."""
        all_embeddings = await self._redis.hgetall(_NS_EMBEDDINGS)
        all_queries = await self._redis.hgetall(_NS_QUERIES)

        best_id: str | None = None
        best_score: float = -1.0

        scope = selected_file or "__all__"

        for raw_id, raw_emb in all_embeddings.items():
            cache_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id

            # File-scope filter: only compare queries for the same file
            raw_meta = all_queries.get(raw_id)
            if raw_meta:
                meta = json.loads(raw_meta)
                cached_scope = meta.get("selected_file", "__all__")
                if cached_scope != scope:
                    continue

            cached_emb = json.loads(raw_emb)
            score = _cosine_similarity(query_embedding, cached_emb)

            if score > best_score:
                best_score = score
                best_id = cache_id

        return best_id, best_score

    async def _load_result(self, cache_id: str) -> dict[str, Any] | None:
        raw = await self._redis.hget(_NS_RESULTS, cache_id)
        if raw:
            return json.loads(raw)
        return None

    async def _incr_stat(self, field: str) -> None:
        await self._redis.hincrby(_NS_STATS, field, 1)
