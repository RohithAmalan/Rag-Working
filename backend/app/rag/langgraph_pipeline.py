"""LangGraph workflow builder for RAG pipeline."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.rag.langgraph_state import AgentState
from app.rag.langgraph_nodes import (
    analyze_query_node,
    create_retrieve_node,
    generate_node,
    validate_node,
    create_exact_match_retrieve_node,
    create_ranking_retrieve_node,
    create_aggregation_retrieve_node,
    create_general_retrieve_node,
)
from app.services.mongo_vector_service import MongoVectorService

logger = logging.getLogger(__name__)


# ============================================================================
# PHASE 1: LINEAR WORKFLOW
# ============================================================================


def build_basic_rag_graph(mongo_service: MongoVectorService) -> Any:
    """Build Phase 1 linear RAG workflow.
    
    Flow:
    START → analyze_query → retrieve → generate → END
    
    Args:
        mongo_service: MongoDB vector search service
        
    Returns:
        Compiled LangGraph workflow
    """
    logger.info("Building Phase 1 LangGraph RAG workflow (linear)")
    
    # Create state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("analyze_query", analyze_query_node)
    workflow.add_node("retrieve", create_retrieve_node(mongo_service))
    workflow.add_node("generate", generate_node)
    
    # Define edges (linear flow)
    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    # Optional: Add memory checkpointing
    # memory = MemorySaver()
    # app = workflow.compile(checkpointer=memory)
    
    # Compile without checkpointing for Phase 1
    app = workflow.compile()
    
    logger.info("Phase 1 workflow compiled successfully")
    return app


# ============================================================================
# PHASE 2: CONDITIONAL ROUTING (Coming Soon)
# ============================================================================


def route_by_intent(state: AgentState) -> str:
    """Router function for conditional edges in Phase 2.
    
    Routes to different retrieval strategies based on query intent.
    """
    intent = state.get("query_intent", "general")
    
    logger.info(f"Routing decision: intent={intent}")
    
    if intent == "exact_lookup":
        return "exact_match_retrieve"
    elif intent == "ranking":
        return "ranking_retrieve"
    elif intent == "aggregation":
        return "aggregation_retrieve"
    else:
        return "general_retrieve"


def route_after_validation(state: AgentState) -> str:
    """Router function after validation node.
    
    Decides whether to refine the query or end the workflow.
    """
    needs_refinement = state.get("needs_refinement", False)
    
    if needs_refinement:
        logger.info("Validation failed, routing to refinement")
        return "refine"  # Future: could route back to analyze_query with refined question
    else:
        logger.info("Validation passed, ending workflow")
        return "end"


def build_advanced_rag_graph(mongo_service: MongoVectorService) -> Any:
    """Build Phase 2 RAG workflow with conditional routing.
    
    Flow:
    START → analyze_query → [route by intent] → retrieve → generate → validate → END
                                ↓
                    exact | ranking | aggregation | general
    
    Args:
        mongo_service: MongoDB vector search service
        
    Returns:
        Compiled LangGraph workflow
    """
    logger.info("Building Phase 2 LangGraph RAG workflow (conditional routing)")
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("analyze_query", analyze_query_node)
    workflow.add_node("exact_match_retrieve", create_exact_match_retrieve_node(mongo_service))
    workflow.add_node("ranking_retrieve", create_ranking_retrieve_node(mongo_service))
    workflow.add_node("aggregation_retrieve", create_aggregation_retrieve_node(mongo_service))
    workflow.add_node("general_retrieve", create_general_retrieve_node(mongo_service))
    workflow.add_node("generate", generate_node)
    workflow.add_node("validate", validate_node)
    
    # Set entry point
    workflow.set_entry_point("analyze_query")
    
    # Add conditional routing from analyze_query based on intent
    workflow.add_conditional_edges(
        "analyze_query",
        route_by_intent,
        {
            "exact_match_retrieve": "exact_match_retrieve",
            "ranking_retrieve": "ranking_retrieve",
            "aggregation_retrieve": "aggregation_retrieve",
            "general_retrieve": "general_retrieve",
        }
    )
    
    # All retrieval nodes go to generate
    workflow.add_edge("exact_match_retrieve", "generate")
    workflow.add_edge("ranking_retrieve", "generate")
    workflow.add_edge("aggregation_retrieve", "generate")
    workflow.add_edge("general_retrieve", "generate")
    
    # Generate goes to validate
    workflow.add_edge("generate", "validate")
    
    # Validate can either end or trigger refinement (for now, just end)
    workflow.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "refine": END,  # Future: route back to analyze_query
            "end": END,
        }
    )
    
    app = workflow.compile()
    logger.info("Phase 2 workflow compiled successfully with conditional routing")
    return app


# ============================================================================
# PHASE 3: MULTI-AGENT WORKFLOW
# ============================================================================


def route_by_complexity(state: Any) -> str:
    """Router: Decide between simple and complex query paths.
    
    Routes to:
    - "simple": Single-file, single-step queries → use Phase 2 routing
    - "complex": Multi-file or multi-step queries → use decomposition
    """
    is_complex = state.get("is_complex_query", False)
    requires_cross_file = state.get("requires_cross_file", False)
    
    if is_complex or requires_cross_file:
        logger.info("Routing to complex multi-agent path")
        return "complex"
    else:
        logger.info("Routing to simple Phase 2 path")
        return "simple"


def route_comparison_type(state: Any) -> str:
    """Router: Decide how to handle comparison results.
    
    Routes to:
    - "generate_comparison": For cross-file comparisons
    - "generate": For standard answer generation
    """
    requires_cross_file = state.get("requires_cross_file", False)
    comparison_results = state.get("comparison_results")
    
    if requires_cross_file and comparison_results:
        logger.info("Routing to comparison-specific generation")
        return "generate_comparison"
    else:
        logger.info("Routing to standard generation")
        return "generate"


def build_multi_agent_graph(mongo_service: MongoVectorService) -> Any:
    """Build Phase 3 multi-agent workflow with parallel execution.
    
    Flow:
    START → detect_complex_query → route_by_complexity
                                        ↓
                        ┌───────────────┴───────────────┐
                        │                               │
                    [simple]                      [complex]
                        │                               │
                  analyze_query                  decompose_query
                        │                               │
                route_by_intent                 parallel_retrieve
                        │                               │
              specialized_retrieve              aggregate_results
                        │                               │
                        └───────────────┬───────────────┘
                                        ↓
                             route_comparison_type
                                        ↓
                        ┌───────────────┴────────────────┐
                        │                                │
              generate_comparison                    generate
                        │                                │
                        └───────────────┬────────────────┘
                                        ↓
                                    validate
                                        ↓
                                       END
    
    Args:
        mongo_service: MongoDB vector search service
        
    Returns:
        Compiled LangGraph workflow
    """
    from langgraph.graph import StateGraph, END
    from app.rag.langgraph_state import MultiStepState
    from app.rag.langgraph_nodes import (
        analyze_query_node,
        detect_complex_query_node,
        decompose_query_node,
        create_exact_match_retrieve_node,
        create_ranking_retrieve_node,
        create_aggregation_retrieve_node,
        create_general_retrieve_node,
        create_parallel_retrieve_node,
        aggregate_results_node,
        generate_node,
        generate_comparison_node,
        validate_node,
    )
    
    logger.info("Building Phase 3 LangGraph multi-agent workflow")
    
    workflow = StateGraph(MultiStepState)
    
    # Add nodes
    workflow.add_node("detect_complex_query", detect_complex_query_node)
    workflow.add_node("analyze_query", analyze_query_node)
    workflow.add_node("decompose_query", decompose_query_node)
    
    # Phase 2 specialized retrieval nodes (for simple path)
    workflow.add_node("exact_match_retrieve", create_exact_match_retrieve_node(mongo_service))
    workflow.add_node("ranking_retrieve", create_ranking_retrieve_node(mongo_service))
    workflow.add_node("aggregation_retrieve", create_aggregation_retrieve_node(mongo_service))
    workflow.add_node("general_retrieve", create_general_retrieve_node(mongo_service))
    
    # Phase 3 multi-agent nodes (for complex path)
    workflow.add_node("parallel_retrieve", create_parallel_retrieve_node(mongo_service))
    workflow.add_node("aggregate_results", aggregate_results_node)
    
    # Generation nodes
    workflow.add_node("generate", generate_node)
    workflow.add_node("generate_comparison", generate_comparison_node)
    workflow.add_node("validate", validate_node)
    
    # Set entry point
    workflow.set_entry_point("detect_complex_query")
    
    # Route by complexity
    workflow.add_conditional_edges(
        "detect_complex_query",
        route_by_complexity,
        {
            "simple": "analyze_query",
            "complex": "decompose_query",
        }
    )
    
    # Simple path: analyze → route by intent → specialized retrieve
    workflow.add_conditional_edges(
        "analyze_query",
        route_by_intent,
        {
            "exact_match_retrieve": "exact_match_retrieve",
            "ranking_retrieve": "ranking_retrieve",
            "aggregation_retrieve": "aggregation_retrieve",
            "general_retrieve": "general_retrieve",
        }
    )
    
    # Complex path: decompose → parallel retrieve → aggregate
    workflow.add_edge("decompose_query", "parallel_retrieve")
    workflow.add_edge("parallel_retrieve", "aggregate_results")
    
    # Both simple and complex paths converge at generation routing
    # Simple path retrieval nodes → route comparison type
    workflow.add_conditional_edges(
        "exact_match_retrieve",
        route_comparison_type,
        {
            "generate_comparison": "generate_comparison",
            "generate": "generate",
        }
    )
    workflow.add_conditional_edges(
        "ranking_retrieve",
        route_comparison_type,
        {
            "generate_comparison": "generate_comparison",
            "generate": "generate",
        }
    )
    workflow.add_conditional_edges(
        "aggregation_retrieve",
        route_comparison_type,
        {
            "generate_comparison": "generate_comparison",
            "generate": "generate",
        }
    )
    workflow.add_conditional_edges(
        "general_retrieve",
        route_comparison_type,
        {
            "generate_comparison": "generate_comparison",
            "generate": "generate",
        }
    )
    
    # Complex path → route comparison type
    workflow.add_conditional_edges(
        "aggregate_results",
        route_comparison_type,
        {
            "generate_comparison": "generate_comparison",
            "generate": "generate",
        }
    )
    
    # Both generation nodes → validate
    workflow.add_edge("generate", "validate")
    workflow.add_edge("generate_comparison", "validate")
    
    # Validate → END
    workflow.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "refine": END,
            "end": END,
        }
    )
    
    app = workflow.compile()
    logger.info("Phase 3 multi-agent workflow compiled successfully")
    return app

