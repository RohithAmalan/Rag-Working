"""Tests for RAG generator functions."""

import pytest
from unittest.mock import patch, MagicMock

from app.rag.generator import (
    _list_all_records_answer,
    _build_system_prompt,
)


def test_list_all_records_answer_detection():
    """Test list all query detection in _list_all_records_answer."""
    # Non-list queries should return None immediately because they aren't list queries
    assert _list_all_records_answer("what is machine learning?", "", {"csv"}) is None
    assert _list_all_records_answer("who is the top salesperson?", "", {"csv"}) is None
    assert _list_all_records_answer("calculate total sales", "", {"csv"}) is None
    assert _list_all_records_answer("list details about employee 123", "", {"csv"}) is None


def test_build_system_prompt_csv():
    """Test system prompt building for CSV/Excel sources."""
    prompt = _build_system_prompt({"csv", "xlsx"})
    
    assert "data analyst" in prompt.lower()
    assert "metadata" in prompt.lower()


def test_build_system_prompt_pdf():
    """Test system prompt building for PDF sources."""
    prompt = _build_system_prompt({"pdf"})
    
    assert "pdf" in prompt.lower()
    assert "document" in prompt.lower()


def test_build_system_prompt_mixed():
    """Test system prompt building for mixed sources."""
    prompt = _build_system_prompt({"csv", "pdf", "xlsx"})
    
    # Should handle mixed sources by using CSV path
    assert len(prompt) > 50  # Should have substantial content
    assert "data analyst" in prompt.lower()

