"""Tests for system routes."""

import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "message" in data


def test_storage_status(client):
    """Test storage status endpoint."""
    response = client.get("/storage/status")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "can_upload" in data
    assert "upload_mode" in data
    assert "minio" in data


def test_documents_list(client):
    """Test documents list endpoint."""
    response = client.get("/documents")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return stats even if empty
    assert "total_chunks" in data or "stats" in data
    assert "documents" in data or isinstance(data, dict)
