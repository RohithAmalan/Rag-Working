"""Tests for system routes."""

import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ok"
    assert "app" in data


def test_storage_status(client):
    """Test storage status endpoint."""
    response = client.get("/storage-status")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "can_upload" in data
    assert "upload_mode" in data
    assert "minio" in data
