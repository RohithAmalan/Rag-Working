"""Cross-encoder reranker for improved retrieval quality."""

import logging
from typing import Dict, List

from app.utils.config import settings
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class RerankerService:
    """Service for reranking retrieved chunks using cross-encoder."""

    def __init__(self):
        """Initialize reranker with cross-encoder model."""
        self.model_name = getattr(
            settings, "reranker_model", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load cross-encoder model."""
        try:
            logger.info(f"Loading reranker model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            logger.info("Reranker model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            raise

    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int = 6,
        score_field: str = "rerank_score",
    ) -> List[Dict]:
        """
        Rerank chunks using cross-encoder.

        Args:
            query: User query
            chunks: List of retrieved chunks
            top_k: Number of top chunks to return
            score_field: Field name to store rerank score

        Returns:
            Reranked chunks with scores
        """
        if not chunks:
            logger.warning("No chunks to rerank")
            return []

        if not self.model:
            logger.warning("Reranker model not loaded, returning original chunks")
            return chunks[:top_k]

        try:
            # Prepare query-chunk pairs
            pairs = [(query, chunk.get("text", "")) for chunk in chunks]

            # Get relevance scores
            logger.info(f"Reranking {len(chunks)} chunks for query: {query[:50]}...")
            scores = self.model.predict(pairs)

            # Add scores to chunks
            for chunk, score in zip(chunks, scores):
                chunk[score_field] = float(score)
                # Keep original score for reference
                if "original_score" not in chunk:
                    chunk["original_score"] = chunk.get("similarity_score", 0.0)

            # Sort by rerank score
            reranked = sorted(chunks, key=lambda x: x[score_field], reverse=True)

            logger.info(
                f"Reranking complete. Top score: {reranked[0][score_field]:.4f}"
            )

            return reranked[:top_k]

        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            # Fallback to original chunks
            return chunks[:top_k]

    def rerank_with_threshold(
        self, query: str, chunks: List[Dict], threshold: float = 0.5, top_k: int = 6
    ) -> List[Dict]:
        """
        Rerank and filter chunks by score threshold.

        Args:
            query: User query
            chunks: List of retrieved chunks
            threshold: Minimum rerank score threshold
            top_k: Maximum number of chunks to return

        Returns:
            Filtered and reranked chunks
        """
        reranked = self.rerank(query, chunks, top_k=len(chunks))

        # Filter by threshold
        filtered = [c for c in reranked if c.get("rerank_score", 0) >= threshold]

        logger.info(
            f"Filtered {len(chunks)} → {len(filtered)} chunks (threshold={threshold})"
        )

        return filtered[:top_k]


# Singleton instance
_reranker_service = None


def get_reranker_service() -> RerankerService:
    """Get singleton reranker service instance."""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
