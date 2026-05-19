"""RAG evaluation framework using RAGAS."""

import logging
from typing import List, Dict, Optional
import asyncio

from datasets import Dataset

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """Evaluate RAG system quality using RAGAS metrics."""
    
    def __init__(self):
        """Initialize evaluator."""
        self.metrics = None
        self._load_metrics()
    
    def _load_metrics(self):
        """Load RAGAS metrics."""
        try:
            from ragas.metrics import (
                answer_relevancy,
                faithfulness,
                context_recall,
                context_precision
            )
            
            self.metrics = {
                'answer_relevancy': answer_relevancy,
                'faithfulness': faithfulness,
                'context_recall': context_recall,
                'context_precision': context_precision
            }
            
            logger.info("RAGAS metrics loaded successfully")
        except ImportError as e:
            logger.warning(f"RAGAS not available: {e}")
            self.metrics = None
    
    async def evaluate_single_query(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict:
        """
        Evaluate a single query-answer pair.
        
        Args:
            question: User question
            answer: Generated answer
            contexts: Retrieved context chunks
            ground_truth: Expected answer (optional)
            
        Returns:
            Dict with metric scores
        """
        if not self.metrics:
            return {"error": "RAGAS not available"}
        
        try:
            from ragas import evaluate as ragas_evaluate
            
            # Prepare dataset
            data = {
                'question': [question],
                'answer': [answer],
                'contexts': [contexts],
            }
            
            if ground_truth:
                data['ground_truth'] = [ground_truth]
            
            dataset = Dataset.from_dict(data)
            
            # Select metrics based on available data
            metrics_to_use = [
                self.metrics['answer_relevancy'],
                self.metrics['faithfulness']
            ]
            
            if ground_truth:
                metrics_to_use.extend([
                    self.metrics['context_recall'],
                    self.metrics['context_precision']
                ])
            
            # Evaluate
            result = await asyncio.to_thread(
                ragas_evaluate,
                dataset,
                metrics=metrics_to_use
            )
            
            # Extract scores
            scores = {
                'answer_relevancy': result['answer_relevancy'],
                'faithfulness': result['faithfulness'],
            }
            
            if ground_truth:
                scores.update({
                    'context_recall': result.get('context_recall'),
                    'context_precision': result.get('context_precision'),
                })
            
            logger.info(f"Evaluation scores: {scores}")
            return scores
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"error": str(e)}
    
    async def evaluate_batch(
        self,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Evaluate multiple test cases.
        
        Args:
            test_cases: List of dicts with keys: question, answer, contexts, ground_truth
            
        Returns:
            Dict with aggregated scores
        """
        if not self.metrics:
            return {"error": "RAGAS not available"}
        
        if not test_cases:
            return {"error": "No test cases provided"}
        
        try:
            from ragas import evaluate as ragas_evaluate
            
            # Prepare batch dataset
            data = {
                'question': [tc['question'] for tc in test_cases],
                'answer': [tc['answer'] for tc in test_cases],
                'contexts': [tc['contexts'] for tc in test_cases],
            }
            
            # Add ground truth if available
            has_ground_truth = all('ground_truth' in tc for tc in test_cases)
            if has_ground_truth:
                data['ground_truth'] = [tc['ground_truth'] for tc in test_cases]
            
            dataset = Dataset.from_dict(data)
            
            # Select metrics
            metrics_to_use = [
                self.metrics['answer_relevancy'],
                self.metrics['faithfulness']
            ]
            
            if has_ground_truth:
                metrics_to_use.extend([
                    self.metrics['context_recall'],
                    self.metrics['context_precision']
                ])
            
            # Evaluate
            result = await asyncio.to_thread(
                ragas_evaluate,
                dataset,
                metrics=metrics_to_use
            )
            
            # Return aggregated scores
            scores = {
                'answer_relevancy': result['answer_relevancy'],
                'faithfulness': result['faithfulness'],
                'num_samples': len(test_cases)
            }
            
            if has_ground_truth:
                scores.update({
                    'context_recall': result.get('context_recall'),
                    'context_precision': result.get('context_precision'),
                })
            
            logger.info(f"Batch evaluation complete: {scores}")
            return scores
            
        except Exception as e:
            logger.error(f"Batch evaluation failed: {e}")
            return {"error": str(e)}
    
    def create_test_case(
        self,
        question: str,
        expected_answer: str,
        additional_info: Optional[Dict] = None
    ) -> Dict:
        """
        Helper to create a test case.
        
        Args:
            question: Test question
            expected_answer: Expected/ground truth answer
            additional_info: Optional metadata
            
        Returns:
            Test case dict
        """
        test_case = {
            'question': question,
            'ground_truth': expected_answer,
            'metadata': additional_info or {}
        }
        
        return test_case


# Singleton instance
_evaluator = None


def get_evaluator() -> RAGEvaluator:
    """Get singleton evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = RAGEvaluator()
    return _evaluator
