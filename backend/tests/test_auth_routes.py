"""Tests for authentication API routes."""

import pytest


def test_login_success(client, valid_credentials):
    """Test successful login."""
    response = client.post("/auth/login", json=valid_credentials)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == valid_credentials["username"]
    assert "message" in data


def test_login_invalid_credentials(client, invalid_credentials):
    """Test login with invalid credentials."""
    response = client.post("/auth/login", json=invalid_credentials)
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_login_missing_fields(client):
    """Test login with missing fields."""
    # Missing password
    response = client.post("/auth/login", json={"username": "admin"})
    assert response.status_code == 422  # Validation error
    
    # Missing username
    response = client.post("/auth/login", json={"password": "admin123"})
    assert response.status_code == 422


def test_logout_success(client, valid_credentials):
    """Test successful logout."""
    # First login
    login_response = client.post("/auth/login", json=valid_credentials)
    token = login_response.json()["access_token"]
    
    # Then logout
    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_logout_no_token(client):
    """Test logout without token."""
    response = client.post("/auth/logout")
    assert response.status_code == 401


def test_logout_invalid_token(client):
    """Test logout with invalid token."""
    response = client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_verify_token_success(client, valid_credentials):
    """Test token verification with valid token."""
    # Login first
    login_response = client.post("/auth/login", json=valid_credentials)
    token = login_response.json()["access_token"]
    
    # Verify token
    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == valid_credentials["username"]
    assert data["is_active"] is True


def test_verify_token_invalid(client):
    """Test token verification with invalid token."""
    response = client.get(
        "/auth/verify",
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_verify_token_no_header(client):
    """Test token verification without authorization header."""
    response = client.get("/auth/verify")
    assert response.status_code == 401


def test_cleanup_endpoint(client):
    """Test token cleanup endpoint."""
    response = client.get("/auth/cleanup")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_full_auth_flow(client, valid_credentials):
    """Test complete authentication flow: login -> verify -> logout."""
    # 1. Login
    login_response = client.post("/auth/login", json=valid_credentials)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 2. Verify token works
    verify_response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert verify_response.status_code == 200
    
    # 3. Logout
    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_response.status_code == 200
    
    # 4. Token should no longer work
    verify_after_logout = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert verify_after_logout.status_code == 401
