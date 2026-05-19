"""LangGraph state definitions for RAG workflow."""

from __future__ import annotations

from typing import TypedDict, Literal


class AgentState(TypedDict, total=False):
    """State schema for LangGraph RAG agent.
    
    This state is passed between nodes and tracks the entire RAG workflow.
    """
    
    # Input
    question: str
    """The user's original question"""
    
    selected_file: str | None
    """File name to scope the search (None = all files)"""
    
    top_k: int
    """Number of chunks to retrieve"""
    
    # Query Analysis
    query_intent: Literal["exact_lookup", "ranking", "aggregation", "general"]
    """Classified intent of the query"""
    
    requires_exact_match: bool
    """Whether query needs exact ID/name/phone lookup"""
    
    requires_ranking: bool
    """Whether query needs numeric ranking (top-k, highest, etc.)"""
    
    extracted_entities: dict[str, list[str]]
    """Extracted IDs, names, phones, emails, etc."""
    
    # Retrieval
    retrieved_chunks: list[dict]
    """Raw chunks from MongoDB vector search"""
    
    retrieval_strategy: Literal["hybrid", "exact", "vector", "ranking"]
    """Strategy used for retrieval"""
    
    # Re-ranking (Phase 2)
    reranked_chunks: list[dict] | None
    """Re-ranked chunks (optional)"""
    
    # Generation
    answer: str
    """Final generated answer"""
    
    citations: list[dict]
    """Source citations for the answer"""
    
    # Validation & Confidence
    confidence: float
    """Confidence score (0-1) for the answer"""
    
    needs_refinement: bool
    """Whether answer needs to be regenerated"""
    
    retry_count: int
    """Number of retry attempts for refinement"""
    
    # Metadata
    workflow_path: list[str]
    """Track which nodes were executed"""
    
    errors: list[str]
    """Any errors encountered during workflow"""


class MultiStepState(AgentState, total=False):
    """Extended state for multi-step queries (Phase 3).
    
    Supports:
    - Query decomposition for complex multi-step questions
    - Parallel retrieval across multiple files
    - Cross-file comparisons
    - Result aggregation and merging
    """
    
    # Query Decomposition
    is_complex_query: bool
    """Whether query requires decomposition"""
    
    sub_queries: list[str]
    """Decomposed sub-queries for complex questions"""
    
    query_dependencies: dict[str, list[str]]
    """Dependency graph for sub-queries"""
    
    # Multi-file Operations
    requires_cross_file: bool
    """Whether query needs data from multiple files"""
    
    comparison_files: list[str]
    """List of files to compare across"""
    
    # Parallel Execution
    sub_results: dict[str, dict]
    """Results from each sub-query (keyed by sub-query or file)"""
    
    parallel_chunks: dict[str, list[dict]]
    """Chunks retrieved from each file in parallel"""
    
    # Aggregation
    requires_aggregation: bool
    """Whether results need to be merged/aggregated"""
    
    aggregation_type: Literal["merge", "compare", "rank", "filter"] | None
    """Type of aggregation needed"""
    
    merged_results: list[dict] | None
    """Final aggregated/merged results"""
    
    # Cross-file Comparison
    comparison_metric: str | None
    """Metric to use for cross-file comparison (e.g., 'unit_price', 'total_price')"""
    
    comparison_results: dict[str, list[dict]] | None
    """Comparison results grouped by file"""
    
    requires_aggregation: bool
    """Whether results need to be combined"""
    
    comparison_files: list[str]
    """Files to compare for cross-file queries"""


class ConversationState(AgentState, total=False):
    """Extended state with conversation history (Phase 4)."""
    
    conversation_history: list[dict[str, str]]
    """Previous Q&A pairs"""
    
    user_feedback: str | None
    """User feedback on previous answer"""
    
    refined_question: str | None
    """Question refined based on history"""
