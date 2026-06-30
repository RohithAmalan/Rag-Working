"""Tests for authentication service."""

from datetime import datetime, timedelta

import pytest

from app.services import auth_service


def test_authenticate_user_valid():
    """Test authentication with valid credentials."""
    assert auth_service.authenticate_user("admin", "admin123") is True
    assert auth_service.authenticate_user("demo", "demo123") is True
    assert auth_service.authenticate_user("user", "user123") is True


def test_authenticate_user_invalid():
    """Test authentication with invalid credentials."""
    assert auth_service.authenticate_user("admin", "wrong") is False
    assert auth_service.authenticate_user("invalid", "admin123") is False
    assert auth_service.authenticate_user("", "") is False


def test_create_access_token():
    """Test access token creation."""
    token = auth_service.create_access_token("admin")

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 20  # URL-safe tokens should be long

    # Verify token is stored
    assert token in auth_service.ACTIVE_TOKENS
    assert auth_service.ACTIVE_TOKENS[token]["username"] == "admin"


def test_verify_token_valid():
    """Test token verification with valid token."""
    token = auth_service.create_access_token("admin")
    username = auth_service.verify_token(token)

    assert username == "admin"


def test_verify_token_invalid():
    """Test token verification with invalid token."""
    username = auth_service.verify_token("invalid-token")
    assert username is None


def test_verify_token_expired():
    """Test token verification with expired token."""
    # Create token
    token = auth_service.create_access_token("admin")

    # Manually expire it
    auth_service.ACTIVE_TOKENS[token]["expires_at"] = datetime.utcnow() - timedelta(
        hours=1
    )

    # Should return None for expired token
    username = auth_service.verify_token(token)
    assert username is None

    # Token should be removed from storage
    assert token not in auth_service.ACTIVE_TOKENS


def test_revoke_token():
    """Test token revocation (logout)."""
    token = auth_service.create_access_token("admin")

    # Verify token exists
    assert token in auth_service.ACTIVE_TOKENS

    # Revoke token
    result = auth_service.revoke_token(token)
    assert result is True

    # Token should be removed
    assert token not in auth_service.ACTIVE_TOKENS

    # Revoking again should return False
    result = auth_service.revoke_token(token)
    assert result is False


def test_cleanup_expired_tokens():
    """Test cleanup of expired tokens."""
    # Create several tokens
    token1 = auth_service.create_access_token("user1")
    token2 = auth_service.create_access_token("user2")
    token3 = auth_service.create_access_token("user3")

    # Expire two of them
    auth_service.ACTIVE_TOKENS[token1]["expires_at"] = datetime.utcnow() - timedelta(
        hours=1
    )
    auth_service.ACTIVE_TOKENS[token2]["expires_at"] = datetime.utcnow() - timedelta(
        hours=2
    )

    # Cleanup
    count = auth_service.cleanup_expired_tokens()

    assert count == 2  # Two tokens expired
    assert token1 not in auth_service.ACTIVE_TOKENS
    assert token2 not in auth_service.ACTIVE_TOKENS
    assert token3 in auth_service.ACTIVE_TOKENS  # Still valid
