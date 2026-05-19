"""Tests for chunking functionality."""

import pytest
import pandas as pd

from app.rag.chunking import chunk_csv_to_rows


def test_chunk_csv_basic():
    """Test basic CSV chunking."""
    # Create sample dataframe
    df = pd.DataFrame({
        "Name": ["John", "Jane", "Bob"],
        "Age": [30, 25, 35],
        "City": ["NYC", "LA", "SF"]
    })
    
    chunks = chunk_csv_to_rows(df, "test.csv")
    
    # Should create one chunk per row
    assert len(chunks) == 3
    
    # Check first chunk
    assert chunks[0]["source_type"] == "csv"
    assert chunks[0]["file_name"] == "test.csv"
    assert "text" in chunks[0]
    assert chunks[0]["rank_priority"] == 1  # CSV is primary source


def test_chunk_csv_with_missing_values():
    """Test CSV chunking with missing values."""
    df = pd.DataFrame({
        "Name": ["John", None, "Bob"],
        "Age": [30, 25, None],
        "City": [None, "LA", "SF"]
    })
    
    chunks = chunk_csv_to_rows(df, "test.csv")
    
    # Should still create chunks
    assert len(chunks) == 3
    
    # Check that None values are handled
    for chunk in chunks:
        assert chunk["text"] is not None
        assert len(chunk["text"]) > 0


def test_chunk_csv_empty_dataframe():
    """Test CSV chunking with empty dataframe."""
    df = pd.DataFrame()
    
    chunks = chunk_csv_to_rows(df, "empty.csv")
    
    # Should return empty list
    assert len(chunks) == 0


def test_chunk_csv_metadata():
    """Test that chunk metadata is correct."""
    df = pd.DataFrame({
        "Product": ["Widget A", "Widget B"],
        "Price": [10.99, 15.99]
    })
    
    chunks = chunk_csv_to_rows(df, "products.xlsx")
    
    for i, chunk in enumerate(chunks):
        assert chunk["row_number"] == i
        assert chunk["rank_priority"] == 1
        assert chunk["source_type"] in ["csv", "xlsx", "excel"]
        assert chunk["file_name"] == "products.xlsx"
