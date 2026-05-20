"""Semantic chunking for better context preservation."""

import logging
from typing import List, Dict, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Split text into semantic chunks based on meaning, not fixed size."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize semantic chunker."""
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load sentence embedding model."""
        try:
            logger.info(f"Loading semantic chunking model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Semantic chunking model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def chunk_text(
        self,
        text: str,
        max_chunk_size: int = 500,
        similarity_threshold: float = 0.7,
        min_sentences: int = 2
    ) -> List[Dict]:
        """
        Split text into semantic chunks.
        
        Args:
            text: Text to chunk
            max_chunk_size: Maximum chunk size in characters
            similarity_threshold: Cosine similarity threshold for grouping sentences
            min_sentences: Minimum sentences per chunk
            
        Returns:
            List of chunk dicts with text and metadata
        """
        if not text or not text.strip():
            return []
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if len(sentences) == 0:
            return []
        
        if len(sentences) == 1:
            return [{"text": text, "sentence_count": 1}]
        
        # Get sentence embeddings
        embeddings = self.model.encode(sentences, show_progress_bar=False)
        
        # Calculate similarity between consecutive sentences
        similarities = self._calculate_similarities(embeddings)
        
        # Find chunk boundaries (low similarity = topic change)
        boundaries = self._find_boundaries(
            similarities,
            threshold=similarity_threshold
        )
        
        # Create chunks from boundaries
        chunks = self._create_chunks(
            sentences,
            boundaries,
            max_chunk_size=max_chunk_size,
            min_sentences=min_sentences
        )
        
        logger.info(f"Split text into {len(chunks)} semantic chunks")
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter (can be improved with spacy/nltk)
        import re
        
        # Split on period, question mark, exclamation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _calculate_similarities(self, embeddings: np.ndarray) -> List[float]:
        """Calculate cosine similarity between consecutive sentences."""
        similarities = []
        
        for i in range(len(embeddings) - 1):
            # Cosine similarity
            sim = np.dot(embeddings[i], embeddings[i + 1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
            )
            similarities.append(float(sim))
        
        return similarities
    
    def _find_boundaries(
        self,
        similarities: List[float],
        threshold: float = 0.7
    ) -> List[int]:
        """Find chunk boundaries where similarity drops below threshold."""
        boundaries = [0]  # Start with first sentence
        
        for i, sim in enumerate(similarities):
            if sim < threshold:
                # Low similarity = topic change
                boundaries.append(i + 1)
        
        boundaries.append(len(similarities) + 1)  # End boundary
        
        return boundaries
    
    def _create_chunks(
        self,
        sentences: List[str],
        boundaries: List[int],
        max_chunk_size: int = 500,
        min_sentences: int = 2
    ) -> List[Dict]:
        """Create chunks from sentence boundaries."""
        chunks = []
        
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            
            chunk_sentences = sentences[start:end]
            
            # Skip very small chunks
            if len(chunk_sentences) < min_sentences:
                # Merge with previous chunk if exists
                if chunks:
                    chunks[-1]['text'] += ' ' + ' '.join(chunk_sentences)
                    chunks[-1]['sentence_count'] += len(chunk_sentences)
                continue
            
            # Join sentences
            chunk_text = ' '.join(chunk_sentences)
            
            # If chunk too large, split by max_chunk_size
            if len(chunk_text) > max_chunk_size:
                # Fall back to character-based splitting
                sub_chunks = self._split_large_chunk(
                    chunk_sentences,
                    max_chunk_size
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    "text": chunk_text,
                    "sentence_count": len(chunk_sentences),
                    "char_count": len(chunk_text)
                })
        
        return chunks
    
    def _split_large_chunk(
        self,
        sentences: List[str],
        max_size: int
    ) -> List[Dict]:
        """Split large chunk by max size."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            if current_size + sentence_len > max_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "sentence_count": len(current_chunk),
                    "char_count": len(chunk_text)
                })
                
                # Start new chunk
                current_chunk = [sentence]
                current_size = sentence_len
            else:
                current_chunk.append(sentence)
                current_size += sentence_len
        
        # Add remaining
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "sentence_count": len(current_chunk),
                "char_count": len(chunk_text)
            })
        
        return chunks
    
    def chunk_document(
        self,
        document: str,
        metadata: Dict = None,
        **kwargs
    ) -> List[Dict]:
        """
        Chunk a full document with metadata preservation.
        
        Args:
            document: Full document text
            metadata: Document metadata to attach to chunks
            **kwargs: Additional chunking parameters
            
        Returns:
            List of chunks with metadata
        """
        chunks = self.chunk_text(document, **kwargs)
        
        # Add metadata to each chunk
        if metadata:
            for i, chunk in enumerate(chunks):
                chunk.update({
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    **metadata
                })
        
        return chunks


# Singleton instance
_semantic_chunker = None


def get_semantic_chunker() -> SemanticChunker:
    """Get singleton semantic chunker instance."""
    global _semantic_chunker
    if _semantic_chunker is None:
        _semantic_chunker = SemanticChunker()
    return _semantic_chunker
