"""LangGraph RAG service - orchestrates the workflow."""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.rag.langgraph_pipeline import (build_advanced_rag_graph,
                                        build_basic_rag_graph,
                                        build_multi_agent_graph)
from app.rag.langgraph_state import AgentState, MultiStepState
from app.services.mongo_vector_service import MongoVectorService

logger = logging.getLogger(__name__)


class LangGraphRAGService:
    """Service to execute RAG queries using LangGraph workflow.

    This wraps the existing MongoDB vector service and generator
    in a LangGraph state machine for better orchestration.

    Supports 3 workflow modes:
    - Phase 1: Linear workflow (basic)
    - Phase 2: Conditional routing (advanced)
    - Phase 3: Multi-agent with parallel execution (multi_agent)
    """

    def __init__(
        self,
        mongo_service: MongoVectorService,
        workflow_mode: Literal["basic", "advanced", "multi_agent"] = "advanced",
    ):
        """Initialize with MongoDB vector service.

        Args:
            mongo_service: MongoDB vector search service
            workflow_mode: Which workflow to use:
                - "basic": Phase 1 linear workflow
                - "advanced": Phase 2 conditional routing (default)
                - "multi_agent": Phase 3 multi-agent with parallel execution
        """
        self.mongo_service = mongo_service
        self.workflow_mode = workflow_mode

        if workflow_mode == "multi_agent":
            self.workflow = build_multi_agent_graph(mongo_service)
            logger.info(
                "LangGraph RAG service initialized with Phase 3 multi-agent workflow"
            )
        elif workflow_mode == "advanced":
            self.workflow = build_advanced_rag_graph(mongo_service)
            logger.info(
                "LangGraph RAG service initialized with Phase 2 advanced routing"
            )
        else:
            self.workflow = build_basic_rag_graph(mongo_service)
            logger.info(
                "LangGraph RAG service initialized with Phase 1 linear workflow"
            )

    async def query(
        self,
        question: str,
        selected_file: str | None = None,
        top_k: int = 15,
    ) -> dict[str, Any]:
        """Execute RAG query using LangGraph workflow.

        Args:
            question: User's question
            selected_file: Optional file name to scope search
            top_k: Number of chunks to retrieve

        Returns:
            dict with answer, citations, confidence, and metadata
        """
        logger.info(
            f"LangGraph query: {question[:100]}... (file={selected_file}, top_k={top_k})"
        )

        # Initialize state (use MultiStepState for Phase 3 compatibility)
        if self.workflow_mode == "multi_agent":
            initial_state: MultiStepState = {
                "question": question,
                "selected_file": selected_file,
                "top_k": top_k,
                "workflow_path": [],
                "errors": [],
                "retry_count": 0,
                "is_complex_query": False,
                "requires_cross_file": False,
                "comparison_files": [],
                "sub_queries": [],
                "parallel_chunks": {},
            }
        else:
            initial_state: AgentState = {
                "question": question,
                "selected_file": selected_file,
                "top_k": top_k,
                "workflow_path": [],
                "errors": [],
                "retry_count": 0,
            }

        try:
            # Execute workflow
            result = await self.workflow.ainvoke(initial_state)

            # Extract results
            answer = result.get("answer", "I don't know based on the uploaded data.")
            citations = result.get("citations", [])
            confidence = result.get("confidence", 0.0)
            retrieved_chunks = result.get("retrieved_chunks", [])
            workflow_path = result.get("workflow_path", [])
            errors = result.get("errors", [])

            logger.info(
                f"LangGraph completed: confidence={confidence:.2f}, "
                f"chunks={len(retrieved_chunks)}, path={workflow_path}"
            )

            if errors:
                logger.warning(f"LangGraph errors: {errors}")

            # Build metadata
            metadata = {
                "query_intent": result.get("query_intent"),
                "retrieval_strategy": result.get("retrieval_strategy"),
                "workflow_path": workflow_path,
                "workflow_mode": self.workflow_mode,
                "requires_ranking": result.get("requires_ranking", False),
                "requires_exact_match": result.get("requires_exact_match", False),
                "errors": errors,
            }

            # Add Phase 3 specific metadata
            if self.workflow_mode == "multi_agent":
                metadata.update(
                    {
                        "is_complex_query": result.get("is_complex_query", False),
                        "requires_cross_file": result.get("requires_cross_file", False),
                        "comparison_files": result.get("comparison_files", []),
                        "aggregation_type": result.get("aggregation_type"),
                        "sub_queries": result.get("sub_queries", []),
                    }
                )

            return {
                "answer": answer,
                "retrieved_chunks": retrieved_chunks,
                "citations": citations,
                "confidence": confidence,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"LangGraph workflow failed: {e}", exc_info=True)
            return {
                "answer": "I encountered an error processing your query.",
                "retrieved_chunks": [],
                "citations": [],
                "confidence": 0.0,
                "metadata": {
                    "error": str(e),
                    "workflow_path": ["error"],
                },
            }
