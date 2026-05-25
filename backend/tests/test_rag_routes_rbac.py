"""Tests for RAG routes with RBAC (Role-Based Access Control)."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.utils.constants import Roles


@pytest.fixture
def admin_token():
    """Mock admin JWT token."""
    return "mock-admin-token"


@pytest.fixture
def user_token():
    """Mock regular user JWT token."""
    return "mock-user-token"


@pytest.fixture
def client_with_mock_auth():
    """Test client with mocked authentication."""
    with patch('app.utils.dependencies.keycloak_service') as mock_keycloak:
        # Default to returning admin user
        mock_keycloak.verify_token.return_value = {
            "username": "admin",
            "sub": "admin-123",
            "email": "admin@test.com",
            "roles": [Roles.ADMIN, Roles.USER],
        }
        yield TestClient(app), mock_keycloak


def test_upload_documents_admin_allowed(client_with_mock_auth):
    """Test that admin users can upload documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token.return_value = {
        "username": "admin",
        "roles": [Roles.ADMIN, Roles.USER],
    }
    
    with patch('app.routes.rag_routes.get_rag_service') as mock_service:
        mock_rag = AsyncMock()
        mock_rag.upload_files.return_value = {
            "message": "Success",
            "files_processed": 1,
            "chunks_created": 10,
        }
        mock_service.return_value = mock_rag
        
        files = {"files": ("test.csv", b"col1,col2\nval1,val2", "text/csv")}
        response = client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": "Bearer admin-token"}
        )
        
        # Should succeed (admin has access)
        assert response.status_code == 200


def test_upload_documents_user_allowed(client_with_mock_auth):
    """Test that regular users can upload documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token.return_value = {
        "username": "user",
        "roles": [Roles.USER],
    }
    
    with patch('app.routes.rag_routes.get_rag_service') as mock_service:
        mock_rag = AsyncMock()
        mock_rag.upload_files.return_value = {
            "message": "Success",
            "files_processed": 1,
            "chunks_created": 10,
        }
        mock_service.return_value = mock_rag
        
        files = {"files": ("test.csv", b"col1,col2\nval1,val2", "text/csv")}
        response = client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": "Bearer user-token"}
        )
        
        # Should succeed (any authenticated user can upload)
        assert response.status_code == 200


def test_upload_documents_no_auth_blocked(client_with_mock_auth):
    """Test that unauthenticated users cannot upload."""
    client, _ = client_with_mock_auth
    
    files = {"files": ("test.csv", b"data", "text/csv")}
    response = client.post("/documents/upload", files=files)
    
    # Should fail (no auth header)
    assert response.status_code == 401


def test_delete_document_admin_allowed(client_with_mock_auth):
    """Test that admin users can delete documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token.return_value = {
        "username": "admin",
        "roles": [Roles.ADMIN, Roles.USER],
    }
    
    with patch('app.routes.rag_routes.get_rag_service') as mock_service:
        mock_rag = AsyncMock()
        mock_rag.delete_document.return_value = {"message": "Deleted"}
        mock_service.return_value = mock_rag
        
        response = client.delete(
            "/documents/doc-123",
            headers={"Authorization": "Bearer admin-token"}
        )
        
        # Should succeed (admin only)
        assert response.status_code == 200


def test_delete_document_user_forbidden(client_with_mock_auth):
    """Test that regular users cannot delete documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token.return_value = {
        "username": "user",
        "roles": [Roles.USER],  # No admin role
    }
    
    response = client.delete(
            "/documents/doc-123",
        headers={"Authorization": "Bearer user-token"}
    )
    
    # Should fail (forbidden - not admin)
    assert response.status_code == 403


def test_query_documents_user_allowed(client_with_mock_auth):
    """Test that authenticated users can query documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token.return_value = {
        "username": "user",
        "roles": [Roles.USER],
    }
    
    with patch('app.routes.rag_routes.get_rag_service') as mock_service:
        mock_rag = AsyncMock()
        mock_rag.query.return_value = {
            "answer": "Test answer",
            "chunks": [],
            "source_types": ["csv"],
        }
        mock_service.return_value = mock_rag
        
        response = client.post(
            "/documents/query",
            json={"question": "What is the sales?"},
            headers={"Authorization": "Bearer user-token"}
        )
        
        # Should succeed (any authenticated user)
        assert response.status_code == 200


def test_query_documents_no_auth_blocked(client_with_mock_auth):
    """Test that unauthenticated users cannot query."""
    client, _ = client_with_mock_auth
    
    response = client.post(
        "/documents/query",
        json={"question": "What is the sales?"}
    )
    
    # Should fail (no auth)
    assert response.status_code == 401


def test_list_documents_user_allowed(client_with_mock_auth):
    """Test that authenticated users can list documents."""
    client, mock_keycloak = client_with_mock_auth
    
    mock_keycloak.verify_token.return_value = {
        "username": "user",
        "roles": [Roles.USER],
    }
    
    with patch('app.routes.rag_routes.get_rag_service') as mock_service:
        mock_rag = AsyncMock()
        mock_rag.get_documents.return_value = {"documents": [], "total_documents": 0}
        mock_service.return_value = mock_rag
        
        response = client.get(
            "/documents",
            headers={"Authorization": "Bearer user-token"}
        )
        
        # Should succeed
        assert response.status_code == 200


def test_list_documents_no_auth_blocked(client_with_mock_auth):
    """Test that unauthenticated users cannot list documents."""
    client, _ = client_with_mock_auth
    
    response = client.get("/documents")
    
    # Should fail
    assert response.status_code == 401
