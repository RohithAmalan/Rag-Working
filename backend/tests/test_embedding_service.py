"""Tests for embedding_service module."""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from app.services.embedding_service import (_embedding_model,
                                            cosine_similarity,
                                            generate_batch_embeddings,
                                            generate_embeddings,
                                            generate_single_embedding,
                                            get_embedding_model)


class TestEmbeddingService:
    """Test suite for embedding service."""

    @pytest.fixture(autouse=True)
    def reset_model(self):
        """Reset global embedding model before each test."""
        import app.services.embedding_service as em

        em._embedding_model = None
        yield
        em._embedding_model = None

    @patch("app.services.embedding_service.SentenceTransformer")
    def test_get_embedding_model_initialization(self, mock_transformer):
        """Test embedding model is initialized correctly."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        result = get_embedding_model()

        assert result == mock_model
        mock_transformer.assert_called_once()

    @patch("app.services.embedding_service.SentenceTransformer")
    def test_get_embedding_model_singleton(self, mock_transformer):
        """Test embedding model is reused (singleton pattern)."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        # Call twice
        result1 = get_embedding_model()
        result2 = get_embedding_model()

        assert result1 == result2
        # Should only be called once
        mock_transformer.assert_called_once()

    @patch("app.services.embedding_service.get_embedding_model")
    def test_generate_embeddings_single_string(self, mock_get_model):
        """Test generating embedding for a single string."""
        mock_model = Mock()
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_model.encode.return_value = mock_embedding
        mock_get_model.return_value = mock_model

        result = generate_embeddings("test text")

        assert isinstance(result, list)
        assert len(result) == 3
        assert result == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once_with("test text", convert_to_numpy=True)

    @patch("app.services.embedding_service.get_embedding_model")
    def test_generate_embeddings_list_of_strings(self, mock_get_model):
        """Test generating embeddings for a list of strings."""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_model.encode.return_value = mock_embeddings
        mock_get_model.return_value = mock_model

        texts = ["text1", "text2"]
        result = generate_embeddings(texts)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_model.encode.assert_called_once_with(texts, convert_to_numpy=True)

    @patch("app.services.embedding_service.get_embedding_model")
    def test_generate_single_embedding(self, mock_get_model):
        """Test generate_single_embedding function."""
        mock_model = Mock()
        mock_embedding = np.array([0.7, 0.8, 0.9])
        mock_model.encode.return_value = mock_embedding
        mock_get_model.return_value = mock_model

        result = generate_single_embedding("single text")

        assert isinstance(result, list)
        assert result == [0.7, 0.8, 0.9]
        mock_model.encode.assert_called_once_with("single text", convert_to_numpy=True)

    @patch("app.services.embedding_service.get_embedding_model")
    def test_generate_batch_embeddings(self, mock_get_model):
        """Test batch embedding generation with custom batch size."""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        mock_model.encode.return_value = mock_embeddings
        mock_get_model.return_value = mock_model

        texts = ["text1", "text2", "text3"]
        result = generate_batch_embeddings(texts, batch_size=16)

        assert isinstance(result, list)
        assert len(result) == 3
        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_model.encode.assert_called_once_with(
            texts, batch_size=16, convert_to_numpy=True
        )

    @patch("app.services.embedding_service.get_embedding_model")
    def test_generate_batch_embeddings_default_batch_size(self, mock_get_model):
        """Test batch embedding uses default batch size."""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2]])
        mock_model.encode.return_value = mock_embeddings
        mock_get_model.return_value = mock_model

        texts = ["text1"]
        result = generate_batch_embeddings(texts)

        mock_model.encode.assert_called_once_with(
            texts, batch_size=32, convert_to_numpy=True
        )

    def test_cosine_similarity_identical_vectors(self):
        """Test cosine similarity returns 1.0 for identical vectors."""
        vec = [1.0, 2.0, 3.0]

        result = cosine_similarity(vec, vec)

        assert isinstance(result, float)
        assert abs(result - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity for orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        result = cosine_similarity(vec1, vec2)

        assert isinstance(result, float)
        assert abs(result - 0.0) < 1e-6

    def test_cosine_similarity_opposite_vectors(self):
        """Test cosine similarity for opposite vectors."""
        vec1 = [1.0, 1.0, 1.0]
        vec2 = [-1.0, -1.0, -1.0]

        result = cosine_similarity(vec1, vec2)

        assert isinstance(result, float)
        assert abs(result - (-1.0)) < 1e-6

    def test_cosine_similarity_different_magnitudes(self):
        """Test cosine similarity is independent of vector magnitude."""
        vec1 = [1.0, 0.0]
        vec2 = [2.0, 0.0]  # Same direction, different magnitude

        result = cosine_similarity(vec1, vec2)

        assert isinstance(result, float)
        assert abs(result - 1.0) < 1e-6

    @patch("app.services.embedding_service.get_embedding_model")
    def test_generate_embeddings_empty_list(self, mock_get_model):
        """Test handling of empty list."""
        mock_model = Mock()
        mock_embeddings = np.array([])
        mock_model.encode.return_value = mock_embeddings
        mock_get_model.return_value = mock_model

        result = generate_embeddings([])

        assert isinstance(result, list)
        mock_model.encode.assert_called_once()
