"""Pytest configuration and fixtures."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import ACTIVE_TOKENS, DEMO_USERS


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_auth_tokens():
    """Reset auth tokens before each test."""
    ACTIVE_TOKENS.clear()
    yield
    ACTIVE_TOKENS.clear()


@pytest.fixture
def valid_credentials():
    """Return valid demo credentials."""
    return {"username": "admin", "password": "admin123"}


@pytest.fixture
def invalid_credentials():
    """Return invalid credentials."""
    return {"username": "invalid", "password": "wrong"}


@pytest.fixture
def mock_rag_service():
    """Create a mock RAG service."""
    service = MagicMock()
    service.upload_files = AsyncMock(
        return_value={
            "message": "Files uploaded successfully",
            "files_processed": 1,
            "chunks_created": 10,
        }
    )
    service.query = AsyncMock(
        return_value={
            "answer": "Test answer",
            "chunks": [],
            "source_types": ["csv"],
        }
    )
    service.get_vector_store_stats = AsyncMock(
        return_value={
            "total_chunks": 100,
            "primary_chunks": 80,
            "secondary_chunks": 20,
        }
    )
    return service


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing."""
    import io

    content = "Name,Age,City\nJohn,30,NYC\nJane,25,LA"
    return io.BytesIO(content.encode())


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF-like file for testing."""
    import io

    return io.BytesIO(b"%PDF-1.4 sample content")
