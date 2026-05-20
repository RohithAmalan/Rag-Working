"""Query expansion for better retrieval coverage."""

import logging
from typing import List, Dict, Set
from groq import Groq

from app.utils.config import settings

logger = logging.getLogger(__name__)


class QueryExpander:
    """Expand user queries into multiple variations for better retrieval."""
    
    def __init__(self):
        """Initialize query expander."""
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.groq_model = settings.groq_model
    
    def expand_query(
        self,
        original_query: str,
        num_variations: int = 3,
        method: str = "llm"
    ) -> List[str]:
        """
        Generate multiple query variations.
        
        Args:
            original_query: User's original question
            num_variations: Number of variations to generate
            method: Expansion method ("llm", "synonyms", "hybrid")
            
        Returns:
            List of query variations (including original)
        """
        if method == "llm":
            return self._expand_with_llm(original_query, num_variations)
        elif method == "synonyms":
            return self._expand_with_synonyms(original_query)
        else:  # hybrid
            llm_queries = self._expand_with_llm(original_query, num_variations - 1)
            synonym_queries = self._expand_with_synonyms(original_query)
            all_queries = [original_query] + llm_queries + synonym_queries
            # Deduplicate and limit
            unique = list(dict.fromkeys(all_queries))
            return unique[:num_variations + 1]
    
    def _expand_with_llm(
        self,
        query: str,
        num_variations: int = 3
    ) -> List[str]:
        """Generate query variations using LLM."""
        prompt = f"""Generate {num_variations} alternative ways to ask this question. 
Make them semantically similar but use different words/phrasing.

Original question: {query}

Requirements:
- Keep the core intent identical
- Use synonyms and paraphrasing
- Vary sentence structure
- Keep them concise
- Do NOT add extra context or change the question type

Return ONLY the alternative questions, one per line, no numbering."""

        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Higher for diversity
                max_tokens=300
            )
            
            variations_text = response.choices[0].message.content.strip()
            
            # Split by newlines and clean
            variations = [
                line.strip().strip('"-').strip()
                for line in variations_text.split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]
            
            # Filter out empty and very short variations
            variations = [v for v in variations if len(v) > 10]
            
            logger.info(f"Generated {len(variations)} query variations for: {query[:50]}...")
            
            return variations[:num_variations]
            
        except Exception as e:
            logger.error(f"LLM query expansion failed: {e}")
            return []
    
    def _expand_with_synonyms(self, query: str) -> List[str]:
        """Generate variations using simple synonym replacement."""
        # Common business/data synonyms
        synonym_map = {
            'highest': ['maximum', 'top', 'largest', 'greatest'],
            'lowest': ['minimum', 'bottom', 'smallest', 'least'],
            'sales': ['revenue', 'purchases', 'transactions'],
            'customer': ['client', 'buyer', 'purchaser'],
            'product': ['item', 'goods', 'merchandise'],
            'total': ['sum', 'aggregate', 'combined'],
            'list': ['show', 'display', 'enumerate'],
            'find': ['get', 'retrieve', 'search for'],
            'what': ['which', 'tell me'],
        }
        
        variations = []
        query_lower = query.lower()
        
        # Try replacing each synonym found
        for word, synonyms in synonym_map.items():
            if word in query_lower:
                for syn in synonyms[:2]:  # Limit to 2 synonyms per word
                    variation = query_lower.replace(word, syn)
                    variations.append(variation.capitalize())
        
        # Deduplicate
        unique = list(dict.fromkeys(variations))
        
        logger.info(f"Generated {len(unique)} synonym variations")
        
        return unique[:3]  # Max 3 variations
    
    def expand_and_merge_results(
        self,
        query: str,
        retrieval_fn,
        num_variations: int = 3,
        top_k_per_query: int = 5
    ) -> List[Dict]:
        """
        Expand query, retrieve for each variation, merge and deduplicate.
        
        Args:
            query: Original query
            retrieval_fn: Function to retrieve chunks (takes query and top_k)
            num_variations: Number of query variations
            top_k_per_query: Chunks to retrieve per variation
            
        Returns:
            Merged and deduplicated chunks
        """
        # Generate variations
        queries = [query] + self.expand_query(query, num_variations)
        
        logger.info(f"Retrieving with {len(queries)} query variations")
        
        # Retrieve for each variation
        all_chunks = []
        seen_texts = set()
        
        for q in queries:
            try:
                chunks = retrieval_fn(q, top_k_per_query)
                
                # Deduplicate by chunk text
                for chunk in chunks:
                    text = chunk.get('text', chunk.get('chunk_text', ''))
                    text_key = text[:200]  # Use first 200 chars as key
                    
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        # Mark which query retrieved it
                        chunk['retrieved_by'] = q
                        all_chunks.append(chunk)
                        
            except Exception as e:
                logger.warning(f"Retrieval failed for variation '{q}': {e}")
        
        logger.info(
            f"Retrieved {len(all_chunks)} unique chunks from "
            f"{len(queries)} query variations"
        )
        
        return all_chunks
    
    def get_best_query_variation(
        self,
        query: str,
        available_fields: Set[str]
    ) -> str:
        """
        Select the best query variation based on available fields.
        
        Useful when you know the schema and want to optimize the query.
        """
        # Simple heuristic: if query mentions fields that exist, keep it
        # Otherwise, try to reformulate
        
        query_lower = query.lower()
        
        # Check if query mentions any available fields
        mentions_field = any(field.lower() in query_lower for field in available_fields)
        
        if mentions_field:
            return query  # Original is good
        
        # Otherwise, generate variations and pick one that mentions fields
        variations = self.expand_query(query, num_variations=5)
        
        for var in variations:
            var_lower = var.lower()
            if any(field.lower() in var_lower for field in available_fields):
                logger.info(f"Selected variation: {var}")
                return var
        
        # Fallback to original
        return query


# Singleton instance
_query_expander = None


def get_query_expander() -> QueryExpander:
    """Get singleton query expander instance."""
    global _query_expander
    if _query_expander is None:
        _query_expander = QueryExpander()
    return _query_expander
