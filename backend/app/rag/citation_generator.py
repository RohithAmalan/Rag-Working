"""Citation-aware answer generation."""

import re
import logging
from typing import Dict, List, Tuple
from groq import Groq

from app.utils.config import settings

logger = logging.getLogger(__name__)


class CitationGenerator:
    """Generate answers with inline citations."""
    
    def __init__(self):
        """Initialize citation generator."""
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.groq_model = settings.groq_model
    
    def generate_with_citations(
        self,
        question: str,
        chunks: List[Dict],
        source_types: set = None
    ) -> Dict:
        """
        Generate answer with inline citations.
        
        Args:
            question: User question
            chunks: Retrieved context chunks
            source_types: Set of source types in chunks
            
        Returns:
            Dict with answer, citations, and metadata
        """
        if not chunks:
            return {
                "answer": "I don't have enough information to answer this question based on the uploaded data.",
                "citations": [],
                "citation_count": 0
            }
        
        # Build numbered context with source attribution
        context_with_refs = self._build_numbered_context(chunks)
        
        # Generate answer with citations
        answer = self._generate_cited_answer(question, context_with_refs, source_types)
        
        # Extract and validate citations
        cited_sources = self._extract_citations(answer, chunks)
        
        return {
            "answer": answer,
            "citations": cited_sources,
            "citation_count": len(cited_sources),
            "total_chunks": len(chunks)
        }
    
    def _build_numbered_context(self, chunks: List[Dict]) -> str:
        """Build context with numbered references."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get('text', '')
            file_name = chunk.get('file_name', 'Unknown')
            source_type = chunk.get('source_type', 'unknown')
            
            # Add row/page info if available
            location = ""
            if 'row_number' in chunk and chunk['row_number'] is not None:
                location = f", Row {chunk['row_number']}"
            elif 'page_number' in chunk and chunk['page_number'] is not None:
                location = f", Page {chunk['page_number']}"
            
            context_parts.append(
                f"[{i}] {text}\n"
                f"(Source: {file_name}, {source_type.upper()}{location})"
            )
        
        return "\n\n".join(context_parts)
    
    def _generate_cited_answer(
        self,
        question: str,
        context_with_refs: str,
        source_types: set = None
    ) -> str:
        """Generate answer with LLM, requesting citations."""
        
        # Determine output format based on source types
        format_instruction = self._get_format_instruction(source_types)
        
        prompt = f"""Answer this question using ONLY the provided sources below.

CRITICAL REQUIREMENTS:
1. Add citations [1], [2], etc. after EVERY factual claim
2. Use [number] format exactly as shown in sources
3. If information is not in the sources, explicitly say so
4. Do not make up or infer information not in sources
5. {format_instruction}

Question: {question}

Sources:
{context_with_refs}

Answer with citations (use [1], [2], etc. format):"""

        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for factual accuracy
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Validate citations exist
            if not re.search(r'\[\d+\]', answer):
                logger.warning("Generated answer has no citations, adding disclaimer")
                answer = f"{answer}\n\n(Note: Based on uploaded documents)"
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating cited answer: {e}")
            return f"Error generating answer: {str(e)}"
    
    def _get_format_instruction(self, source_types: set = None) -> str:
        """Get format instruction based on source types."""
        if not source_types:
            return "Provide a clear, well-structured answer"
        
        if source_types == {"pdf"}:
            return "Extract and synthesize information from the document clearly"
        elif source_types.intersection({"csv", "xlsx", "excel"}):
            return "Present data insights with specific numbers, metrics, or values in bullet points or numbered lists"
        else:
            return "Combine information from all sources coherently"
    
    def _extract_citations(self, answer: str, chunks: List[Dict]) -> List[Dict]:
        """Extract which sources were actually cited."""
        # Find all citation numbers in answer
        citation_numbers = set(map(int, re.findall(r'\[(\d+)\]', answer)))
        
        # Map to actual source chunks
        cited_sources = []
        for num in sorted(citation_numbers):
            if 1 <= num <= len(chunks):
                chunk = chunks[num - 1].copy()
                chunk['citation_number'] = num
                cited_sources.append(chunk)
        
        return cited_sources
    
    def format_citations_for_display(self, citations: List[Dict]) -> List[Dict]:
        """Format citations for frontend display."""
        formatted = []
        
        for cite in citations:
            formatted.append({
                "number": cite.get('citation_number', 0),
                "file_name": cite.get('file_name', 'Unknown'),
                "source_type": cite.get('source_type', 'unknown'),
                "text_preview": cite.get('text', '')[:200] + "..." if len(cite.get('text', '')) > 200 else cite.get('text', ''),
                "row_number": cite.get('row_number'),
                "page_number": cite.get('page_number'),
            })
        
        return formatted


# Singleton instance
_citation_generator = None


def get_citation_generator() -> CitationGenerator:
    """Get singleton citation generator instance."""
    global _citation_generator
    if _citation_generator is None:
        _citation_generator = CitationGenerator()
    return _citation_generator
