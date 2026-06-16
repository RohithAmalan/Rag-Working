"""API routes for RAG evaluation."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.rag.evaluator import get_evaluator
from app.utils.dependencies import get_current_user
from app.utils.constants import Roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluationRequest(BaseModel):
    """Request to evaluate a single query."""
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None


class TestCase(BaseModel):
    """Test case for batch evaluation."""
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None


class BatchEvaluationRequest(BaseModel):
    """Request to evaluate multiple queries."""
    test_cases: List[TestCase]


@router.post("/evaluate-query")
async def evaluate_query(
    request: EvaluationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Evaluate a single query-answer pair (requires authentication).
    
    Returns RAGAS metrics:
    - answer_relevancy: How relevant is the answer to the question?
    - faithfulness: Is the answer grounded in the provided context?
    - context_recall: Does context contain necessary information? (requires ground_truth)
    - context_precision: Is the context focused and relevant? (requires ground_truth)
    """
    try:
        evaluator = get_evaluator()
        
        scores = await evaluator.evaluate_single_query(
            question=request.question,
            answer=request.answer,
            contexts=request.contexts,
            ground_truth=request.ground_truth
        )
        
        return {
            "success": True,
            "scores": scores,
            "question": request.question[:100]  # Preview
        }
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-batch")
async def evaluate_batch(
    request: BatchEvaluationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Evaluate multiple query-answer pairs in batch.
    
    Returns aggregated RAGAS metrics across all test cases.
    """
    try:
        evaluator = get_evaluator()
        
        # Convert Pydantic models to dicts
        test_cases = [tc.dict() for tc in request.test_cases]
        
        scores = await evaluator.evaluate_batch(test_cases)
        
        return {
            "success": True,
            "aggregated_scores": scores,
            "num_test_cases": len(test_cases)
        }
        
    except Exception as e:
        logger.error(f"Batch evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics-info")
async def get_metrics_info():
    """Get information about available evaluation metrics."""
    return {
        "available_metrics": [
            {
                "name": "answer_relevancy",
                "description": "Measures how relevant the answer is to the question",
                "range": "[0, 1]",
                "higher_is_better": True,
                "requires_ground_truth": False
            },
            {
                "name": "faithfulness",
                "description": "Measures if the answer is grounded in the provided context (no hallucinations)",
                "range": "[0, 1]",
                "higher_is_better": True,
                "requires_ground_truth": False
            },
            {
                "name": "context_recall",
                "description": "Measures if the retrieved context contains all necessary information",
                "range": "[0, 1]",
                "higher_is_better": True,
                "requires_ground_truth": True
            },
            {
                "name": "context_precision",
                "description": "Measures if the retrieved context is focused and relevant",
                "range": "[0, 1]",
                "higher_is_better": True,
                "requires_ground_truth": True
            }
        ],
        "framework": "RAGAS (Retrieval Augmented Generation Assessment)"
    }
