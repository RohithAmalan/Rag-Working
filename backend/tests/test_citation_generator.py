"""Tests for citation generator."""

import pytest
from app.rag.citation_generator import get_citation_generator


class TestCitationGenerator:
    """Test citation generation functionality."""

    def test_citation_generator_initialization(self):
        """Test citation generator can be initialized."""
        gen = get_citation_generator()
        assert gen is not None

    def test_generate_with_citations(self):
        """Test answer generation with citations."""
        gen = get_citation_generator()

        chunks = [
            {
                "text": "Python is a high-level programming language created by Guido van Rossum.",
                "file_name": "python_intro.pdf",
                "source_type": "pdf",
                "page_number": 1,
            },
            {
                "text": "Python is widely used in data science and machine learning.",
                "file_name": "python_intro.pdf",
                "source_type": "pdf",
                "page_number": 2,
            },
        ]

        question = "What is Python?"

        result = gen.generate_with_citations(question, chunks, source_types={"pdf"})

        assert "answer" in result
        assert "citations" in result
        assert "citation_count" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0

    def test_generate_with_empty_chunks(self):
        """Test generation with no chunks."""
        gen = get_citation_generator()

        result = gen.generate_with_citations("test question", [], source_types=set())

        assert "don't have enough information" in result["answer"].lower()
        assert result["citation_count"] == 0
        assert len(result["citations"]) == 0

    def test_format_citations_for_display(self):
        """Test citation formatting for frontend."""
        gen = get_citation_generator()

        citations = [
            {
                "citation_number": 1,
                "text": "Long text " * 50,
                "file_name": "test.pdf",
                "source_type": "pdf",
                "page_number": 5,
            }
        ]

        formatted = gen.format_citations_for_display(citations)

        assert len(formatted) == 1
        assert formatted[0]["number"] == 1
        assert formatted[0]["file_name"] == "test.pdf"
        assert len(formatted[0]["text_preview"]) <= 203  # 200 + "..."
