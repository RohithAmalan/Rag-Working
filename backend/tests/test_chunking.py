"""Tests for chunking functionality."""

import pytest
import pandas as pd

from app.rag.chunking import dataframe_to_documents


def test_chunk_csv_basic():
    """Test basic CSV chunking."""
    # Create sample dataframe
    df = pd.DataFrame({
        "Name": ["John", "Jane", "Bob"],
        "Age": [30, 25, 35],
        "City": ["NYC", "LA", "SF"]
    })
    
    chunks = dataframe_to_documents(df, "test.csv", "csv")
    
    # Should create one chunk per row
    assert len(chunks) == 3
    
    # Check first chunk
    assert chunks[0]["metadata"]["source_type"] == "csv"
    assert chunks[0]["metadata"]["file_name"] == "test.csv"
    assert "page_content" in chunks[0]
    assert chunks[0]["metadata"]["source_priority"] == "primary"


def test_chunk_csv_with_missing_values():
    """Test CSV chunking with missing values."""
    df = pd.DataFrame({
        "Name": ["John", None, "Bob"],
        "Age": [30, 25, None],
        "City": [None, "LA", "SF"]
    })
    
    chunks = dataframe_to_documents(df, "test.csv", "csv")
    
    # Should still create chunks
    assert len(chunks) == 3
    
    # Check that None values are handled
    for chunk in chunks:
        assert chunk["page_content"] is not None
        assert len(chunk["page_content"]) > 0


def test_chunk_csv_empty_dataframe():
    """Test CSV chunking with empty dataframe."""
    df = pd.DataFrame()
    
    chunks = dataframe_to_documents(df, "empty.csv", "csv")
    
    # Should return empty list
    assert len(chunks) == 0


def test_chunk_csv_metadata():
    """Test that chunk metadata is correct."""
    df = pd.DataFrame({
        "Product": ["Widget A", "Widget B"],
        "Price": [10.99, 15.99]
    })
    
    chunks = dataframe_to_documents(df, "products.xlsx", "excel")
    
    for i, chunk in enumerate(chunks):
        assert chunk["metadata"]["row_index"] == i
        assert chunk["metadata"]["source_priority"] == "primary"
        assert chunk["metadata"]["source_type"] == "excel"
        assert chunk["metadata"]["file_name"] == "products.xlsx"
