"""Tests for reranker service."""

import pytest

from app.rag.reranker import get_reranker_service


class TestRerankerService:
    """Test reranker functionality."""

    def test_reranker_initialization(self):
        """Test reranker service can be initialized."""
        reranker = get_reranker_service()
        assert reranker is not None
        assert reranker.model is not None

    def test_rerank_chunks(self):
        """Test reranking functionality."""
        reranker = get_reranker_service()

        chunks = [
            {"text": "Python is a programming language", "similarity_score": 0.7},
            {"text": "The weather is sunny today", "similarity_score": 0.8},
            {"text": "Machine learning uses Python", "similarity_score": 0.6},
        ]

        query = "What is Python used for?"

        reranked = reranker.rerank(query, chunks, top_k=2)

        assert len(reranked) == 2
        assert all("rerank_score" in chunk for chunk in reranked)
        # First chunk should be more relevant
        assert reranked[0]["text"] in [
            "Python is a programming language",
            "Machine learning uses Python",
        ]

    def test_rerank_empty_chunks(self):
        """Test reranking with empty chunks."""
        reranker = get_reranker_service()

        reranked = reranker.rerank("test query", [], top_k=5)

        assert reranked == []

    def test_rerank_with_threshold(self):
        """Test reranking with score threshold."""
        reranker = get_reranker_service()

        chunks = [
            {"text": "Python is a programming language", "similarity_score": 0.7},
            {"text": "The weather is sunny today", "similarity_score": 0.8},
        ]

        query = "What is Python?"

        # High threshold should filter out irrelevant chunks
        reranked = reranker.rerank_with_threshold(
            query, chunks, threshold=0.5, top_k=10
        )

        assert isinstance(reranked, list)
        assert all("rerank_score" in chunk for chunk in reranked)
