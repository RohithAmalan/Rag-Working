"""Tests for evaluation routes."""

from unittest.mock import AsyncMock, patch

import pytest
from app.main import app
from fastapi.testclient import TestClient


class TestEvaluationRoutes:
    """Test suite for evaluation API routes."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_evaluator(self):
        """Create a mock evaluator."""
        with patch("app.routes.evaluation_routes.get_evaluator") as mock:
            evaluator = AsyncMock()
            mock.return_value = evaluator
            yield evaluator

    def test_evaluate_query_success(self, client, mock_evaluator):
        """Test successful query evaluation."""
        mock_evaluator.evaluate_single_query = AsyncMock(
            return_value={
                "answer_relevancy": 0.85,
                "faithfulness": 0.90,
            }
        )

        response = client.post(
            "/evaluation/evaluate-query",
            json={
                "question": "What is Python?",
                "answer": "Python is a programming language",
                "contexts": ["Python is a high-level programming language"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "scores" in data
        assert "answer_relevancy" in data["scores"]

    def test_evaluate_query_with_ground_truth(self, client, mock_evaluator):
        """Test query evaluation with ground truth."""
        mock_evaluator.evaluate_single_query = AsyncMock(
            return_value={
                "answer_relevancy": 0.85,
                "faithfulness": 0.90,
                "context_recall": 0.88,
                "context_precision": 0.92,
            }
        )

        response = client.post(
            "/evaluation/evaluate-query",
            json={
                "question": "What is Python?",
                "answer": "Python is a programming language",
                "contexts": ["Python is a high-level programming language"],
                "ground_truth": "Python is a high-level, interpreted programming language",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "context_recall" in data["scores"]
        assert "context_precision" in data["scores"]

    def test_evaluate_query_error_handling(self, client, mock_evaluator):
        """Test error handling in query evaluation."""
        mock_evaluator.evaluate_single_query = AsyncMock(
            side_effect=Exception("Evaluation failed")
        )

        response = client.post(
            "/evaluation/evaluate-query",
            json={"question": "Test", "answer": "Test answer", "contexts": ["context"]},
        )

        assert response.status_code == 500

    def test_evaluate_batch_success(self, client, mock_evaluator):
        """Test successful batch evaluation."""
        mock_evaluator.evaluate_batch = AsyncMock(
            return_value={
                "answer_relevancy": 0.80,
                "faithfulness": 0.85,
            }
        )

        response = client.post(
            "/evaluation/evaluate-batch",
            json={
                "test_cases": [
                    {"question": "Q1", "answer": "A1", "contexts": ["C1"]},
                    {"question": "Q2", "answer": "A2", "contexts": ["C2"]},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["num_test_cases"] == 2
        assert "aggregated_scores" in data

    def test_evaluate_batch_empty_cases(self, client, mock_evaluator):
        """Test batch evaluation with empty test cases."""
        mock_evaluator.evaluate_batch = AsyncMock(return_value={})

        response = client.post("/evaluation/evaluate-batch", json={"test_cases": []})

        assert response.status_code == 200
        data = response.json()
        assert data["num_test_cases"] == 0

    def test_evaluate_batch_error(self, client, mock_evaluator):
        """Test error handling in batch evaluation."""
        mock_evaluator.evaluate_batch = AsyncMock(
            side_effect=Exception("Batch evaluation failed")
        )

        response = client.post(
            "/evaluation/evaluate-batch",
            json={
                "test_cases": [{"question": "Q1", "answer": "A1", "contexts": ["C1"]}]
            },
        )

        assert response.status_code == 500

    def test_get_metrics_info(self, client):
        """Test retrieving metrics information."""
        response = client.get("/evaluation/metrics-info")

        assert response.status_code == 200
        data = response.json()
        assert "available_metrics" in data
        assert len(data["available_metrics"]) > 0

    def test_evaluate_query_missing_required_fields(self, client):
        """Test evaluation with missing required fields."""
        response = client.post(
            "/evaluation/evaluate-query",
            json={
                "question": "What is Python?",
                # Missing answer and contexts
            },
        )

        assert response.status_code == 422  # Validation error

    def test_evaluate_query_invalid_data_types(self, client):
        """Test evaluation with invalid data types."""
        response = client.post(
            "/evaluation/evaluate-query",
            json={
                "question": "What is Python?",
                "answer": "Python is great",
                "contexts": "This should be a list",  # Wrong type
            },
        )

        assert response.status_code == 422  # Validation error
