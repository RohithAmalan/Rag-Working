"""Tests for RAG generator functions."""

import pytest
from unittest.mock import patch, MagicMock

from app.rag.generator import (
    _detect_list_all_query,
    _build_system_prompt,
)


def test_detect_list_all_query():
    """Test list all query detection."""
    # Should detect "list all" queries
    assert _detect_list_all_query("list all employees") is True
    assert _detect_list_all_query("show all products") is True
    assert _detect_list_all_query("give me all customers") is True
    assert _detect_list_all_query("show me every sale") is True
    
    # Should NOT detect regular queries
    assert _detect_list_all_query("what is machine learning?") is False
    assert _detect_list_all_query("who is the top salesperson?") is False
    assert _detect_list_all_query("calculate total sales") is False


def test_build_system_prompt_csv():
    """Test system prompt building for CSV/Excel sources."""
    prompt = _build_system_prompt({"csv", "xlsx"})
    
    assert "structured data" in prompt.lower() or "csv" in prompt.lower()
    assert "bullet" in prompt.lower() or "list" in prompt.lower()


def test_build_system_prompt_pdf():
    """Test system prompt building for PDF sources."""
    prompt = _build_system_prompt({"pdf"})
    
    assert "pdf" in prompt.lower()
    assert "document" in prompt.lower()


def test_build_system_prompt_mixed():
    """Test system prompt building for mixed sources."""
    prompt = _build_system_prompt({"csv", "pdf", "xlsx"})
    
    # Should handle mixed sources
    assert len(prompt) > 50  # Should have substantial content
    assert "answer" in prompt.lower()
