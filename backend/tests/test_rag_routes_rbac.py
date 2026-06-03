"""Tests for RAG routes with RBAC (Role-Based Access Control)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.utils.constants import Roles


@pytest.fixture(autouse=True)
def cleanup_rag_service():
    """Ensure rag_service is cleared after each test."""
    app.state.rag_service = None
    yield
    app.state.rag_service = None


@pytest.fixture
def client_with_mock_auth():
    """Test client with mocked authentication."""
    with patch('app.utils.dependencies.keycloak_service') as mock_keycloak:
        # Default mock verify_token returns admin user
        mock_keycloak.verify_token = AsyncMock(return_value={
            "username": "admin",
            "sub": "admin-123",
            "email": "admin@test.com",
            "roles": [Roles.ADMIN, Roles.USER],
        })
        mock_keycloak.is_enabled.return_value = True
        yield TestClient(app), mock_keycloak


def test_upload_documents_admin_allowed(client_with_mock_auth):
    """Test that admin users can upload documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token = AsyncMock(return_value={
        "username": "admin",
        "roles": [Roles.ADMIN, Roles.USER],
    })
    
    mock_rag = AsyncMock()
    mock_rag.upload_and_process_files.return_value = {
        "processed_files": 1,
        "documents": [{"filename": "test.csv", "chunks_stored": 10}],
        "errors": [],
    }
    app.state.rag_service = mock_rag
    
    files = {"files": ("test.csv", b"col1,col2\nval1,val2", "text/csv")}
    response = client.post(
        "/upload",
        files=files,
        headers={"Authorization": "Bearer admin-token"}
    )
    
    assert response.status_code == 200
    assert response.json()["processed_files"] == 1


def test_upload_documents_user_forbidden_for_non_admin(client_with_mock_auth):
    """Test that regular users cannot upload documents (since it is require_admin)."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token = AsyncMock(return_value={
        "username": "user",
        "roles": [Roles.USER],  # No admin role
    })
    
    mock_rag = AsyncMock()
    app.state.rag_service = mock_rag
    
    files = {"files": ("test.csv", b"col1,col2\nval1,val2", "text/csv")}
    response = client.post(
        "/upload",
        files=files,
        headers={"Authorization": "Bearer user-token"}
    )
    
    # upload_documents has require_admin dependency, so regular user should be forbidden
    assert response.status_code == 403


def test_upload_documents_no_auth_blocked(client_with_mock_auth):
    """Test that unauthenticated users cannot upload."""
    client, _ = client_with_mock_auth
    
    mock_rag = AsyncMock()
    app.state.rag_service = mock_rag
    
    files = {"files": ("test.csv", b"data", "text/csv")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 401


def test_delete_document_admin_allowed(client_with_mock_auth):
    """Test that admin users can delete documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token = AsyncMock(return_value={
        "username": "admin",
        "roles": [Roles.ADMIN, Roles.USER],
    })
    
    mock_rag = AsyncMock()
    mock_rag.delete_document.return_value = {"deleted_chunks": 10}
    app.state.rag_service = mock_rag
    
    response = client.delete(
        "/documents/doc-123",
        headers={"Authorization": "Bearer admin-token"}
    )
    
    assert response.status_code == 200
    assert response.json()["deleted_chunks"] == 10


def test_delete_document_user_forbidden(client_with_mock_auth):
    """Test that regular users cannot delete documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token = AsyncMock(return_value={
        "username": "user",
        "roles": [Roles.USER],  # No admin role
    })
    
    mock_rag = AsyncMock()
    app.state.rag_service = mock_rag
    
    response = client.delete(
        "/documents/doc-123",
        headers={"Authorization": "Bearer user-token"}
    )
    
    assert response.status_code == 403


def test_query_documents_user_allowed(client_with_mock_auth):
    """Test that authenticated users can query documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token = AsyncMock(return_value={
        "username": "user",
        "roles": [Roles.USER],
    })
    
    mock_rag = AsyncMock()
    mock_rag.search_and_retrieve.return_value = [
        {
            "chunk_text": "Hello World",
            "similarity_score": 0.95,
            "source": "test.csv",
            "metadata": {"file_type": "csv", "source_type": "csv"},
        }
    ]
    app.state.rag_service = mock_rag
    
    with patch('app.routes.rag_routes.generate_answer') as mock_gen_answer:
        mock_gen_answer.return_value = "Mocked LLM Answer"
        
        response = client.post(
            "/query",
            json={"question": "What is the sales?"},
            headers={"Authorization": "Bearer user-token"}
        )
        
        assert response.status_code == 200
        assert response.json()["answer"] == "Mocked LLM Answer"


def test_query_documents_no_auth_blocked(client_with_mock_auth):
    """Test that unauthenticated users cannot query."""
    client, _ = client_with_mock_auth
    
    mock_rag = AsyncMock()
    app.state.rag_service = mock_rag
    
    response = client.post(
        "/query",
        json={"question": "What is the sales?"}
    )
    
    assert response.status_code == 401


def test_list_documents_user_allowed(client_with_mock_auth):
    """Test that authenticated users can list documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token = AsyncMock(return_value={
        "username": "user",
        "roles": [Roles.USER],
    })
    
    mock_rag = AsyncMock()
    mock_rag.get_all_documents.return_value = [
        {
            "_id": "doc-1",
            "filename": "test.csv",
            "file_type": "csv",
            "metadata": {"chunks_stored": 5, "storage_backend": "local"},
            "path": "/app/uploads/test.csv",
        }
    ]
    mock_rag.get_vector_store_stats.return_value = {"total_chunks": 5, "total_documents": 1}
    app.state.rag_service = mock_rag
    
    response = client.get(
        "/documents",
        headers={"Authorization": "Bearer user-token"}
    )
    
    assert response.status_code == 200
    assert response.json()["total_chunks"] == 5
    assert len(response.json()["documents"]) == 1


def test_list_documents_no_auth_blocked(client_with_mock_auth):
    """Test that unauthenticated users cannot list documents."""
    client, _ = client_with_mock_auth
    
    mock_rag = AsyncMock()
    app.state.rag_service = mock_rag
    
    response = client.get("/documents")
    
    assert response.status_code == 401

