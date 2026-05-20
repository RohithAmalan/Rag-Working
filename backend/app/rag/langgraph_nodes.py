"""LangGraph nodes for RAG workflow - Phase 1 & 2 with Advanced Features."""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from app.rag.langgraph_state import AgentState
from app.services.mongo_vector_service import MongoVectorService
from app.rag.generator import generate_answer
from app.rag.reranker import get_reranker_service
from app.rag.citation_generator import get_citation_generator
from app.rag.query_expansion import get_query_expander

logger = logging.getLogger(__name__)


# ============================================================================
# PHASE 1: BASIC LINEAR WORKFLOW
# ============================================================================


async def analyze_query_node(state: AgentState) -> dict[str, Any]:
    """Node 1: Analyze query and extract intent.
    
    Determines:
    - Query intent (exact_lookup, ranking, aggregation, general)
    - Whether exact matching is needed
    - Whether ranking is needed
    - Extracted entities (IDs, names, phones)
    """
    question = state["question"]
    q_lower = question.lower()
    
    # Track workflow
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("analyze_query")
    
    # Extract entities using existing patterns
    from app.services.mongo_vector_service import _extract_exact_terms
    entities = _extract_exact_terms(question)
    
    # Detect ranking intent
    requires_ranking = any(token in q_lower for token in ["top", "highest", "lowest", "maximum", "minimum", "max", "min"]) and \
                      any(token in q_lower for token in ["price", "sales", "quantity", "profit", "revenue", "cost", "discount"])
    
    # Detect exact lookup intent
    requires_exact_match = bool(entities["ids"]) or bool(entities["phones"]) or bool(entities["emails"])
    
    # Classify intent
    if requires_exact_match:
        query_intent = "exact_lookup"
    elif requires_ranking:
        query_intent = "ranking"
    elif any(token in q_lower for token in ["all", "list all", "count", "total", "sum", "average"]):
        query_intent = "aggregation"
    else:
        query_intent = "general"
    
    logger.info(f"Query analysis: intent={query_intent}, ranking={requires_ranking}, exact={requires_exact_match}")
    
    return {
        "query_intent": query_intent,
        "requires_exact_match": requires_exact_match,
        "requires_ranking": requires_ranking,
        "extracted_entities": entities,
        "workflow_path": workflow_path,
        "errors": state.get("errors", []),
    }


async def retrieve_node(
    state: AgentState,
    mongo_service: MongoVectorService,
    use_query_expansion: bool = True,
) -> dict[str, Any]:
    """Node 2: Retrieve chunks using query expansion + hybrid search + reranking.
    
    Steps:
    1. [Optional] Expand query into multiple variations
    2. Retrieve candidates using hybrid search (per variation if expanded)
    3. Merge and deduplicate results
    4. Rerank using cross-encoder
    5. Return top-k best chunks
    """
    question = state["question"]
    selected_file = state.get("selected_file")
    top_k = state.get("top_k", 6)
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("retrieve")
    
    try:
        # Step 1: Query Expansion (if enabled)
        queries = [question]
        if use_query_expansion:
            expander = get_query_expander()
            queries = [question] + expander.expand_query(question, num_variations=2)
            logger.info(f"Expanded to {len(queries)} query variations")
        
        # Step 2: Retrieve candidates for each query variation
        all_chunks = []
        seen_ids = set()
        candidate_count_per_query = min((top_k * 3) // max(len(queries), 1), 30)
        
        for query in queries:
            logger.info(f"Retrieving {candidate_count_per_query} candidates for: {query[:50]}...")
            
            chunks = await mongo_service.search_chunks(
                query_text=query,
                top_k=candidate_count_per_query,
                required_file_name=selected_file,
                source_priority="primary",
            )
            
            # Deduplicate by chunk ID
            for chunk in chunks:
                chunk_id = chunk.get('_id', chunk.get('chunk_index', ''))
                if chunk_id and chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    all_chunks.append(chunk)
        
        logger.info(f"Retrieved {len(all_chunks)} unique chunks from {len(queries)} queries")
        
        # Rerank chunks using cross-encoder
        reranker = get_reranker_service()
        reranked_chunks = reranker.rerank(
            query=question,
            chunks=chunks,
            top_k=top_k
        )
        
        # Determine strategy used
        if state.get("requires_exact_match"):
            strategy = "exact+rerank"
        elif state.get("requires_ranking"):
            strategy = "ranking+rerank"
        elif chunks and chunks[0].get("similarity_score", 0) > 0.95:
            strategy = "hybrid+rerank"
        else:
            strategy = "vector+rerank"
        
        logger.info(
            f"Retrieved and reranked {len(chunks)} → {len(reranked_chunks)} chunks "
            f"(strategy: {strategy}, top score: {reranked_chunks[0].get('rerank_score', 0):.3f})"
        )
        
        return {
            "retrieved_chunks": reranked_chunks,
            "retrieval_strategy": strategy,
            "workflow_path": workflow_path,
            "errors": state.get("errors", []),
        }
        
    except Exception as e:
        logger.error(f"Retrieval/reranking failed: {e}")
        errors = state.get("errors", [])
        errors.append(f"Retrieval error: {str(e)}")
        
        return {
            "retrieved_chunks": [],
            "retrieval_strategy": "vector",
            "workflow_path": workflow_path,
            "errors": errors,
        }


async def generate_node(state: AgentState) -> dict[str, Any]:
    """Node 3: Generate answer with citations from retrieved chunks.
    
    Uses citation-aware generation for better answer quality.
    """
    from app.utils.config import settings
    
    question = state["question"]
    chunks = state.get("retrieved_chunks", [])
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("generate")
    
    try:
        # Get citation generator
        citation_gen = get_citation_generator()
        
        # Prepare chunks for citation generation
        formatted_chunks = []
        source_types = set()
        
        for chunk in chunks:
            # Extract text from chunk
            text = chunk.get("chunk_text", "")
            if not text:
                text = chunk.get("text", "")
            
            # Extract metadata
            metadata = chunk.get("metadata", {})
            file_name = metadata.get("file_name", "unknown")
            source_type = metadata.get("source_type", "unknown")
            
            if source_type:
                source_types.add(source_type)
            
            # Format chunk for citation generator
            formatted_chunks.append({
                "text": text,
                "file_name": file_name,
                "source_type": source_type,
                "row_number": metadata.get("row_index"),
                "page_number": metadata.get("page_number"),
                "similarity_score": chunk.get("similarity_score", 0),
                "rerank_score": chunk.get("rerank_score", 0),
            })
        
        # Generate answer with citations
        result = citation_gen.generate_with_citations(
            question=question,
            chunks=formatted_chunks,
            source_types=source_types
        )
        
        answer = result["answer"]
        citations = citation_gen.format_citations_for_display(result["citations"])
        
        # Calculate confidence based on rerank scores
        if not chunks:
            confidence = 0.0
        elif "don't know" in answer.lower() or "not in" in answer.lower():
            confidence = 0.3
        else:
            # Use average rerank score
            rerank_scores = [c.get("rerank_score", 0) for c in formatted_chunks]
            if rerank_scores:
                confidence = min(sum(rerank_scores) / len(rerank_scores), 1.0)
            else:
                confidence = 0.5
        
        logger.info(
            f"Generated answer with {len(citations)} citations "
            f"(confidence: {confidence:.2f})"
        )
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "needs_refinement": False,
            "workflow_path": workflow_path,
            "errors": state.get("errors", []),
        }
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        # Build context string from chunks
        context_parts = []
        source_types = set()
        
        for chunk in chunks:
            content = chunk.get("chunk_text", "")
            if content:
                context_parts.append(content)
            
            # Track source types
            source_type = chunk.get("metadata", {}).get("source_type", "")
            if source_type:
                source_types.add(source_type)
        
        context = "\n\n".join(context_parts) if context_parts else ""
        
        # Call generate_answer with proper parameters
        answer = generate_answer(
            question=question,
            context=context,
            groq_api_key=settings.groq_api_key,
            groq_model=settings.groq_model,
            source_types=source_types,
        )
        
        # Build citations
        citations = [
            {
                "file_name": chunk.get("metadata", {}).get("file_name", "unknown"),
                "source_type": chunk.get("metadata", {}).get("source_type", "unknown"),
                "sheet_name": chunk.get("metadata", {}).get("sheet_name"),
                "row_index": chunk.get("metadata", {}).get("row_index"),
                "chunk_index": chunk.get("chunk_index", 0),
            }
            for chunk in chunks
        ]
        
        # Calculate basic confidence
        if not chunks:
            confidence = 0.0
        elif "don't know" in answer.lower():
            confidence = 0.3
        else:
            # Use average similarity score
            scores = [c.get("similarity_score", 0) for c in chunks]
            confidence = sum(scores) / len(scores) if scores else 0.5
        
        logger.info(f"Generated answer with confidence: {confidence:.2f}")
        
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "needs_refinement": False,
            "workflow_path": workflow_path,
            "errors": state.get("errors", []),
        }
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        errors = state.get("errors", [])
        errors.append(f"Generation error: {str(e)}")
        
        return {
            "answer": "I encountered an error generating the answer.",
            "citations": [],
            "confidence": 0.0,
            "needs_refinement": False,
            "workflow_path": workflow_path,
            "errors": errors,
        }


# ============================================================================
# HELPER: Create retrieval node with injected service
# ============================================================================


def create_retrieve_node(mongo_service: MongoVectorService):
    """Factory to create retrieve node with MongoDB service injected."""
    async def node(state: AgentState) -> dict[str, Any]:
        return await retrieve_node(state, mongo_service)
    return node


# ============================================================================
# PHASE 2: SPECIALIZED RETRIEVAL NODES
# ============================================================================


async def exact_match_retrieve_node(
    state: AgentState,
    mongo_service: MongoVectorService,
) -> dict[str, Any]:
    """Phase 2: Optimized retrieval for exact ID/phone/email/name lookups.
    
    This node prioritizes exact matching before falling back to vector search.
    """
    question = state["question"]
    selected_file = state.get("selected_file")
    top_k = state.get("top_k", 15)
    entities = state.get("extracted_entities", {})
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("exact_match_retrieve")
    
    logger.info(f"Exact match retrieval for entities: {entities}")
    
    try:
        # Use the hybrid search which already optimizes for exact matches
        chunks = await mongo_service.search_chunks(
            query_text=question,
            top_k=top_k,
            required_file_name=selected_file,
            source_priority="primary",
        )
        
        # Filter to only high-confidence exact matches
        exact_chunks = [c for c in chunks if c.get("similarity_score", 0) > 0.9]
        
        if exact_chunks:
            logger.info(f"Found {len(exact_chunks)} exact matches")
            chunks = exact_chunks[:top_k]
        
        return {
            "retrieved_chunks": chunks,
            "retrieval_strategy": "exact",
            "workflow_path": workflow_path,
            "errors": state.get("errors", []),
        }
        
    except Exception as e:
        logger.error(f"Exact match retrieval failed: {e}")
        errors = state.get("errors", [])
        errors.append(f"Exact match error: {str(e)}")
        
        return {
            "retrieved_chunks": [],
            "retrieval_strategy": "exact",
            "workflow_path": workflow_path,
            "errors": errors,
        }


async def ranking_retrieve_node(
    state: AgentState,
    mongo_service: MongoVectorService,
) -> dict[str, Any]:
    """Phase 2: Optimized retrieval for ranking queries (top-k, highest, lowest).
    
    This node uses the fast path metric ranking logic.
    """
    question = state["question"]
    selected_file = state.get("selected_file")
    top_k = state.get("top_k", 15)
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("ranking_retrieve")
    
    logger.info(f"Ranking retrieval for query: {question}")
    
    try:
        # Use hybrid search which includes the ranking fast path
        chunks = await mongo_service.search_chunks(
            query_text=question,
            top_k=top_k,
            required_file_name=selected_file,
            source_priority="primary",
        )
        
        logger.info(f"Ranking retrieval found {len(chunks)} chunks")
        
        return {
            "retrieved_chunks": chunks,
            "retrieval_strategy": "ranking",
            "workflow_path": workflow_path,
            "errors": state.get("errors", []),
        }
        
    except Exception as e:
        logger.error(f"Ranking retrieval failed: {e}")
        errors = state.get("errors", [])
        errors.append(f"Ranking retrieval error: {str(e)}")
        
        return {
            "retrieved_chunks": [],
            "retrieval_strategy": "ranking",
            "workflow_path": workflow_path,
            "errors": errors,
        }


async def aggregation_retrieve_node(
    state: AgentState,
    mongo_service: MongoVectorService,
) -> dict[str, Any]:
    """Phase 2: Optimized retrieval for aggregation queries (count, sum, average, all).
    
    Retrieves more chunks to ensure complete coverage for aggregation.
    """
    question = state["question"]
    selected_file = state.get("selected_file")
    top_k = state.get("top_k", 15)
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("aggregation_retrieve")
    
    logger.info(f"Aggregation retrieval for query: {question}")
    
    try:
        # For aggregation, retrieve more chunks to ensure complete coverage
        extended_top_k = max(top_k, 30)
        
        chunks = await mongo_service.search_chunks(
            query_text=question,
            top_k=extended_top_k,
            required_file_name=selected_file,
            source_priority="primary",
        )
        
        logger.info(f"Aggregation retrieval found {len(chunks)} chunks (extended from {top_k} to {extended_top_k})")
        
        return {
            "retrieved_chunks": chunks,
            "retrieval_strategy": "aggregation",
            "workflow_path": workflow_path,
            "errors": state.get("errors", []),
        }
        
    except Exception as e:
        logger.error(f"Aggregation retrieval failed: {e}")
        errors = state.get("errors", [])
        errors.append(f"Aggregation retrieval error: {str(e)}")
        
        return {
            "retrieved_chunks": [],
            "retrieval_strategy": "aggregation",
            "workflow_path": workflow_path,
            "errors": errors,
        }


async def general_retrieve_node(
    state: AgentState,
    mongo_service: MongoVectorService,
) -> dict[str, Any]:
    """Phase 2: General semantic search retrieval (fallback).
    
    Uses pure vector similarity search for general questions.
    """
    question = state["question"]
    selected_file = state.get("selected_file")
    top_k = state.get("top_k", 15)
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("general_retrieve")
    
    logger.info(f"General retrieval for query: {question}")
    
    try:
        chunks = await mongo_service.search_chunks(
            query_text=question,
            top_k=top_k,
            required_file_name=selected_file,
            source_priority="primary",
        )
        
        logger.info(f"General retrieval found {len(chunks)} chunks")
        
        return {
            "retrieved_chunks": chunks,
            "retrieval_strategy": "vector",
            "workflow_path": workflow_path,
            "errors": state.get("errors", []),
        }
        
    except Exception as e:
        logger.error(f"General retrieval failed: {e}")
        errors = state.get("errors", [])
        errors.append(f"General retrieval error: {str(e)}")
        
        return {
            "retrieved_chunks": [],
            "retrieval_strategy": "vector",
            "workflow_path": workflow_path,
            "errors": errors,
        }


# ============================================================================
# PHASE 2: VALIDATION NODE
# ============================================================================


async def validate_node(state: AgentState) -> dict[str, Any]:
    """Phase 2: Validate answer confidence and decide if refinement is needed.
    
    If confidence is too low and we haven't retried yet, mark for refinement.
    """
    confidence = state.get("confidence", 0.0)
    answer = state.get("answer", "")
    workflow_path = state.get("workflow_path", [])
    retry_count = state.get("retry_count", 0)
    
    workflow_path.append("validate")
    
    # Confidence thresholds
    LOW_CONFIDENCE_THRESHOLD = 0.4
    MAX_RETRIES = 1
    
    # Check if answer indicates uncertainty
    has_uncertainty = any(phrase in answer.lower() for phrase in [
        "don't know",
        "cannot find",
        "no information",
        "not available",
    ])
    
    # Decide if refinement is needed
    needs_refinement = (
        (confidence < LOW_CONFIDENCE_THRESHOLD or has_uncertainty) and
        retry_count < MAX_RETRIES
    )
    
    if needs_refinement:
        logger.warning(
            f"Low confidence ({confidence:.2f}) or uncertainty detected. "
            f"Retry {retry_count + 1}/{MAX_RETRIES}"
        )
    else:
        logger.info(f"Validation passed: confidence={confidence:.2f}")
    
    return {
        "needs_refinement": needs_refinement,
        "retry_count": retry_count + 1 if needs_refinement else retry_count,
        "workflow_path": workflow_path,
        "errors": state.get("errors", []),
    }


# ============================================================================
# PHASE 2: FACTORY HELPERS
# ============================================================================


def create_exact_match_retrieve_node(mongo_service: MongoVectorService):
    """Factory for exact match retrieval node."""
    async def node(state: AgentState) -> dict[str, Any]:
        return await exact_match_retrieve_node(state, mongo_service)
    return node


def create_ranking_retrieve_node(mongo_service: MongoVectorService):
    """Factory for ranking retrieval node."""
    async def node(state: AgentState) -> dict[str, Any]:
        return await ranking_retrieve_node(state, mongo_service)
    return node


def create_aggregation_retrieve_node(mongo_service: MongoVectorService):
    """Factory for aggregation retrieval node."""
    async def node(state: AgentState) -> dict[str, Any]:
        return await aggregation_retrieve_node(state, mongo_service)
    return node


def create_general_retrieve_node(mongo_service: MongoVectorService):
    """Factory for general retrieval node."""
    async def node(state: AgentState) -> dict[str, Any]:
        return await general_retrieve_node(state, mongo_service)
    return node


# ============================================================================
# PHASE 3: MULTI-AGENT WORKFLOW
# ============================================================================


async def detect_complex_query_node(state: AgentState) -> dict[str, Any]:
    """Node: Detect if query requires multi-step decomposition.
    
    Detects:
    - Cross-file comparisons ("compare X between file1 and file2")
    - Multi-step operations ("find X then show Y")
    - Complex aggregations across multiple files
    """
    from app.rag.langgraph_state import MultiStepState
    
    question = state["question"]
    q_lower = question.lower()
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("detect_complex_query")
    
    # Detect cross-file comparison
    requires_cross_file = any([
        "compare" in q_lower and "between" in q_lower,
        "compare" in q_lower and ("and" in q_lower or "vs" in q_lower),
        all(word in q_lower for word in ["across", "files"]),
        all(word in q_lower for word in ["in", "both"]),
    ])
    
    # Detect multi-step operations
    is_complex_query = any([
        requires_cross_file,
        all(word in q_lower for word in ["find", "then"]),
        all(word in q_lower for word in ["show", "and", "also"]),
        q_lower.count("and") >= 2,  # Multiple conditions
    ])
    
    # Extract files mentioned in query (if any)
    comparison_files = []
    if requires_cross_file:
        # Look for .xlsx file mentions
        import re
        file_pattern = r'([A-Za-z0-9\-_\s]+\.xlsx)'
        matches = re.findall(file_pattern, question, re.IGNORECASE)
        comparison_files = [f.strip() for f in matches]
    
    logger.info(
        f"Complex query detection: is_complex={is_complex_query}, "
        f"cross_file={requires_cross_file}, files={comparison_files}"
    )
    
    return {
        "is_complex_query": is_complex_query,
        "requires_cross_file": requires_cross_file,
        "comparison_files": comparison_files,
        "workflow_path": workflow_path,
    }


async def decompose_query_node(state: AgentState) -> dict[str, Any]:
    """Node: Decompose complex query into sub-queries.
    
    Uses LLM to break down complex questions into executable sub-queries.
    """
    from app.rag.langgraph_state import MultiStepState
    from groq import AsyncGroq
    from app.utils.config import GROQ_API_KEY
    
    question = state["question"]
    requires_cross_file = state.get("requires_cross_file", False)
    comparison_files = state.get("comparison_files", [])
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("decompose_query")
    
    # Build decomposition prompt
    if requires_cross_file and comparison_files:
        prompt = f"""You are a query decomposition expert. Break down this complex cross-file comparison query into simple sub-queries.

User Question: {question}

Files to compare: {', '.join(comparison_files)}

Generate 2-4 sub-queries that:
1. Extract the specific data needed from each file
2. Are simple enough to answer from a single file
3. Can be combined to answer the original question

Return ONLY a JSON array of sub-queries, nothing else.
Example: ["query 1", "query 2", "query 3"]"""
    else:
        prompt = f"""You are a query decomposition expert. Break down this complex query into simple sub-queries.

User Question: {question}

Generate 2-4 sub-queries that:
1. Are simpler than the original
2. Build upon each other logically
3. Can be combined to answer the original question

Return ONLY a JSON array of sub-queries, nothing else.
Example: ["query 1", "query 2", "query 3"]"""
    
    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        
        import json
        content = response.choices[0].message.content.strip()
        
        # Extract JSON array from response
        if content.startswith("[") and content.endswith("]"):
            sub_queries = json.loads(content)
        else:
            # Try to find JSON array in response
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                sub_queries = json.loads(match.group(0))
            else:
                # Fallback: split by original query structure
                sub_queries = [question]
        
        logger.info(f"Query decomposed into {len(sub_queries)} sub-queries: {sub_queries}")
        
    except Exception as e:
        logger.error(f"Query decomposition failed: {e}")
        # Fallback to original query
        sub_queries = [question]
    
    return {
        "sub_queries": sub_queries,
        "workflow_path": workflow_path,
    }


def create_parallel_retrieve_node(mongo_service: MongoVectorService):
    """Factory: Create parallel retrieval node for multi-file queries."""
    
    async def parallel_retrieve_node(state: AgentState) -> dict[str, Any]:
        """Node: Retrieve chunks from multiple files in parallel.
        
        Uses asyncio to fetch results from multiple files simultaneously.
        """
        from app.rag.langgraph_state import MultiStepState
        import asyncio
        
        question = state["question"]
        comparison_files = state.get("comparison_files", [])
        selected_file = state.get("selected_file")
        top_k = state.get("top_k", 15)
        query_intent = state.get("query_intent", "general")
        
        workflow_path = state.get("workflow_path", [])
        workflow_path.append("parallel_retrieve")
        
        # Determine files to search
        files_to_search = []
        if comparison_files:
            files_to_search = comparison_files
        elif selected_file:
            # Single file query, use standard retrieval
            files_to_search = [selected_file]
        else:
            # No specific files, search all (handled by None)
            files_to_search = [None]
        
        logger.info(f"Parallel retrieval from {len(files_to_search)} sources: {files_to_search}")
        
        # Parallel retrieval tasks
        async def retrieve_from_file(file_name: str | None) -> tuple[str | None, list[dict]]:
            """Retrieve chunks from a specific file."""
            try:
                chunks = await mongo_service.hybrid_search(
                    query=question,
                    top_k=top_k,
                    file_name=file_name,
                )
                logger.info(f"Retrieved {len(chunks)} chunks from {file_name or 'all files'}")
                return (file_name, chunks)
            except Exception as e:
                logger.error(f"Parallel retrieval from {file_name} failed: {e}")
                return (file_name, [])
        
        # Execute parallel retrievals
        tasks = [retrieve_from_file(file) for file in files_to_search]
        results = await asyncio.gather(*tasks)
        
        # Organize results by file
        parallel_chunks = {}
        all_chunks = []
        
        for file_name, chunks in results:
            key = file_name or "all_files"
            parallel_chunks[key] = chunks
            all_chunks.extend(chunks)
        
        total_chunks = len(all_chunks)
        logger.info(f"Parallel retrieval complete: {total_chunks} total chunks from {len(results)} sources")
        
        return {
            "parallel_chunks": parallel_chunks,
            "retrieved_chunks": all_chunks,  # Combined for compatibility
            "retrieval_strategy": "parallel",
            "workflow_path": workflow_path,
        }
    
    return parallel_retrieve_node


async def aggregate_results_node(state: AgentState) -> dict[str, Any]:
    """Node: Aggregate and merge results from multiple sources.
    
    Handles:
    - Deduplication of similar chunks
    - Ranking across all sources
    - Grouping by file for comparison
    """
    from app.rag.langgraph_state import MultiStepState
    
    parallel_chunks = state.get("parallel_chunks", {})
    requires_cross_file = state.get("requires_cross_file", False)
    query_intent = state.get("query_intent", "general")
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("aggregate_results")
    
    if not parallel_chunks:
        logger.warning("No parallel chunks to aggregate")
        return {
            "merged_results": [],
            "aggregation_type": None,
            "workflow_path": workflow_path,
        }
    
    # Determine aggregation strategy
    if requires_cross_file and query_intent == "ranking":
        aggregation_type = "compare"
    elif requires_cross_file:
        aggregation_type = "merge"
    elif query_intent == "ranking":
        aggregation_type = "rank"
    else:
        aggregation_type = "merge"
    
    logger.info(f"Aggregating results with strategy: {aggregation_type}")
    
    # Perform aggregation
    if aggregation_type == "compare":
        # Keep chunks grouped by file for comparison
        comparison_results = parallel_chunks
        merged_results = []
        
        # Extract top results from each file
        for file_name, chunks in parallel_chunks.items():
            if chunks:
                # Sort by score and take top items
                sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
                top_chunks = sorted_chunks[:5]  # Top 5 from each file
                merged_results.extend(top_chunks)
        
        logger.info(f"Comparison aggregation: {len(merged_results)} total chunks from {len(parallel_chunks)} files")
        
    elif aggregation_type == "rank":
        # Merge all chunks and rank by score
        all_chunks = []
        for chunks in parallel_chunks.values():
            all_chunks.extend(chunks)
        
        # Sort by score and deduplicate
        sorted_chunks = sorted(all_chunks, key=lambda x: x.get("score", 0), reverse=True)
        
        # Simple deduplication by content similarity
        merged_results = []
        seen_content = set()
        for chunk in sorted_chunks:
            content_key = chunk.get("content", "")[:100]  # First 100 chars as key
            if content_key not in seen_content:
                merged_results.append(chunk)
                seen_content.add(content_key)
        
        comparison_results = None
        logger.info(f"Ranking aggregation: {len(merged_results)} unique chunks after deduplication")
        
    else:  # merge
        # Simple merge without ranking
        all_chunks = []
        for chunks in parallel_chunks.values():
            all_chunks.extend(chunks)
        merged_results = all_chunks
        comparison_results = None
        logger.info(f"Merge aggregation: {len(merged_results)} total chunks")
    
    return {
        "merged_results": merged_results,
        "aggregation_type": aggregation_type,
        "comparison_results": comparison_results if aggregation_type == "compare" else None,
        "retrieved_chunks": merged_results,  # Update for generation
        "workflow_path": workflow_path,
    }


async def generate_comparison_node(state: AgentState) -> dict[str, Any]:
    """Node: Generate answer for cross-file comparison queries.
    
    Specialized generation that highlights differences/similarities between files.
    """
    from app.rag.langgraph_state import MultiStepState
    
    question = state["question"]
    comparison_results = state.get("comparison_results", {})
    comparison_files = state.get("comparison_files", [])
    merged_results = state.get("merged_results", [])
    
    workflow_path = state.get("workflow_path", [])
    workflow_path.append("generate_comparison")
    
    if not comparison_results and not merged_results:
        logger.warning("No results to compare")
        return {
            "answer": "I don't have enough data to compare across the specified files.",
            "confidence": 0.2,
            "citations": [],
            "workflow_path": workflow_path,
        }
    
    # Build comparison context
    if comparison_results:
        context_parts = []
        for file_name, chunks in comparison_results.items():
            context_parts.append(f"\n=== Data from {file_name} ===\n")
            for chunk in chunks[:5]:  # Top 5 from each file
                context_parts.append(chunk.get("content", ""))
        context = "\n".join(context_parts)
    else:
        # Fallback to merged results
        context = "\n\n".join([chunk.get("content", "") for chunk in merged_results[:10]])
    
    # Generate comparison answer
    try:
        answer, confidence, citations = await generate_answer(
            question=question,
            context=context,
            use_strict_prompt=True,
        )
        
        logger.info(f"Comparison answer generated with confidence: {confidence:.2f}")
        
    except Exception as e:
        logger.error(f"Comparison generation failed: {e}")
        answer = "I encountered an error while generating the comparison."
        confidence = 0.0
        citations = []
    
    return {
        "answer": answer,
        "confidence": confidence,
        "citations": citations,
        "workflow_path": workflow_path,
    }


def create_parallel_retrieve_factory(mongo_service: MongoVectorService):
    """Factory helper for parallel retrieval node."""
    return create_parallel_retrieve_node(mongo_service)

