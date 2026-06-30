"""Tests for semantic chunking."""

import pytest

from app.rag.semantic_chunker import get_semantic_chunker


class TestSemanticChunker:
    """Test semantic chunking functionality."""

    def test_chunker_initialization(self):
        """Test semantic chunker can be initialized."""
        chunker = get_semantic_chunker()
        assert chunker is not None
        assert chunker.model is not None

    def test_split_sentences(self):
        """Test sentence splitting."""
        chunker = get_semantic_chunker()

        text = "This is sentence one. This is sentence two! Is this sentence three?"

        sentences = chunker._split_sentences(text)

        assert len(sentences) == 3
        assert "sentence one" in sentences[0]
        assert "sentence two" in sentences[1]
        assert "sentence three" in sentences[2]

    def test_chunk_text(self):
        """Test semantic text chunking."""
        chunker = get_semantic_chunker()

        text = """
        Python is a high-level programming language. It was created by Guido van Rossum.
        Python is widely used in data science. Machine learning frameworks like TensorFlow use Python.
        JavaScript is a web programming language. It runs in browsers.
        """

        chunks = chunker.chunk_text(
            text, max_chunk_size=200, similarity_threshold=0.6, min_sentences=1
        )

        assert isinstance(chunks, list)
        assert len(chunks) > 0

        # Check chunk structure
        for chunk in chunks:
            assert "text" in chunk
            assert "sentence_count" in chunk
            assert isinstance(chunk["text"], str)
            assert len(chunk["text"]) > 0

    def test_chunk_document(self):
        """Test document chunking with metadata."""
        chunker = get_semantic_chunker()

        document = "First sentence. Second sentence. Third sentence."
        metadata = {"file_name": "test.txt", "source_type": "txt"}

        chunks = chunker.chunk_document(document, metadata=metadata)

        assert isinstance(chunks, list)

        # Check metadata is attached
        if chunks:
            assert chunks[0].get("file_name") == "test.txt"
            assert chunks[0].get("source_type") == "txt"
            assert "chunk_index" in chunks[0]
            assert "total_chunks" in chunks[0]

    def test_empty_text(self):
        """Test chunking empty text."""
        chunker = get_semantic_chunker()

        chunks = chunker.chunk_text("")

        assert chunks == []

    def test_single_sentence(self):
        """Test chunking single sentence."""
        chunker = get_semantic_chunker()

        text = "This is a single sentence."

        chunks = chunker.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0]["text"] == text
        assert chunks[0]["sentence_count"] == 1

    def test_singleton_pattern(self):
        """Test that chunker uses singleton pattern."""
        chunker1 = get_semantic_chunker()
        chunker2 = get_semantic_chunker()

        assert chunker1 is chunker2
