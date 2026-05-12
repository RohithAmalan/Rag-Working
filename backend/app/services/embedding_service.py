"""Embedding generation service."""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING

import numpy as np
from sentence_transformers import SentenceTransformer

from app.utils.config import settings

if TYPE_CHECKING:
    pass

warnings.filterwarnings(
    "ignore",
    message=r"resource_tracker: There appear to be .* leaked semaphore objects",
    category=UserWarning,
)

logger = logging.getLogger(__name__)

_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Get or initialize the embedding model."""
    global _embedding_model

    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _embedding_model = SentenceTransformer(settings.embedding_model)

    return _embedding_model


def generate_embeddings(texts: str | list[str]) -> list[float] | list[list[float]]:
    """Generate embeddings for text(s).

    Args:
        texts: Single text or list of texts to embed

    Returns:
        Single embedding vector or list of embedding vectors
    """
    model = get_embedding_model()

    # Handle single string
    if isinstance(texts, str):
        embedding = model.encode(texts, convert_to_numpy=True)
        return embedding.tolist()

    # Handle list of strings
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [emb.tolist() for emb in embeddings]


def generate_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats
    """
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def generate_batch_embeddings(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Generate embeddings for multiple texts with batching.

    Args:
        texts: List of texts to embed
        batch_size: Batch size for processing

    Returns:
        List of embedding vectors
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
    return [emb.tolist() for emb in embeddings]


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Similarity score between 0 and 1
    """
    arr1 = np.array(vec1)
    arr2 = np.array(vec2)

    # Normalize vectors
    arr1_norm = arr1 / (np.linalg.norm(arr1) + 1e-10)
    arr2_norm = arr2 / (np.linalg.norm(arr2) + 1e-10)

    # Calculate cosine similarity
    similarity = np.dot(arr1_norm, arr2_norm)
    return float(similarity)
