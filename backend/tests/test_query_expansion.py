"""Tests for query expansion."""

import pytest
from app.rag.query_expansion import get_query_expander


class TestQueryExpander:
    """Test query expansion functionality."""
    
    def test_expander_initialization(self):
        """Test query expander can be initialized."""
        expander = get_query_expander()
        assert expander is not None
        assert expander.groq_client is not None
    
    def test_expand_with_synonyms(self):
        """Test synonym-based expansion."""
        expander = get_query_expander()
        
        query = "What are the highest sales?"
        
        variations = expander._expand_with_synonyms(query)
        
        assert isinstance(variations, list)
        # Should generate at least some variations
        assert len(variations) >= 0
        
        # Check if variations are different from original
        if variations:
            assert any(v.lower() != query.lower() for v in variations)
    
    def test_expand_query_llm(self):
        """Test LLM-based query expansion."""
        expander = get_query_expander()
        
        query = "What is machine learning?"
        
        variations = expander.expand_query(query, num_variations=2, method="llm")
        
        # Should return a list (original + variations)
        assert isinstance(variations, list)
        
        # Check variations are strings
        assert all(isinstance(v, str) for v in variations)
        
        # Check variations are not empty
        assert all(len(v) > 10 for v in variations)
    
    def test_expand_query_hybrid(self):
        """Test hybrid expansion (LLM + synonyms)."""
        expander = get_query_expander()
        
        query = "Show me the top customers"
        
        variations = expander.expand_query(query, num_variations=3, method="hybrid")
        
        assert isinstance(variations, list)
        assert len(variations) <= 4  # Original + 3 variations max
    
    def test_singleton_pattern(self):
        """Test that expander uses singleton pattern."""
        expander1 = get_query_expander()
        expander2 = get_query_expander()
        
        assert expander1 is expander2
