"""Tests for Keycloak service."""

import pytest
from unittest.mock import patch, MagicMock
from jose import jwt

from app.services.keycloak_service import KeycloakService
from app.utils.constants import Roles


@pytest.fixture
def keycloak_service():
    """Create a KeycloakService instance for testing."""
    return KeycloakService()


@pytest.fixture
def mock_jwks():
    """Mock JWKS response."""
    return {
        "keys": [
            {
                "kid": "test-key-id",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": "test-n-value",
                "e": "AQAB",
            }
        ]
    }


@pytest.fixture
def valid_token_payload():
    """Valid JWT token payload."""
    return {
        "sub": "user-123",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "realm_access": {
            "roles": [Roles.USER, "offline_access"],
        },
        "iss": "http://localhost:8080/realms/rag-realm",
        "exp": 9999999999,  # Far future
        "iat": 1000000000,
    }


def test_verify_token_success(keycloak_service, valid_token_payload):
    """Test successful token verification."""
    with patch('app.services.keycloak_service.httpx.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "keys": [{"kid": "key1", "n": "test", "e": "AQAB"}]
        }
        mock_get.return_value = mock_response
        
        with patch('app.services.keycloak_service.jwt.decode') as mock_decode:
            mock_decode.return_value = valid_token_payload
            
            result = keycloak_service.verify_token("test-token")
            
            assert result["username"] == "testuser"
            assert result["sub"] == "user-123"
            assert result["email"] == "test@example.com"
            assert Roles.USER in result["roles"]
            assert "offline_access" not in result["roles"]  # System role filtered


def test_verify_token_extracts_roles(keycloak_service):
    """Test that verify_token correctly extracts roles from realm_access."""
    payload = {
        "sub": "user-456",
        "preferred_username": "admin",
        "email": "admin@example.com",
        "realm_access": {
            "roles": [Roles.ADMIN, Roles.USER, "uma_authorization"],
        },
        "iss": "http://localhost:8080/realms/rag-realm",
        "exp": 9999999999,
    }
    
    with patch('app.services.keycloak_service.httpx.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kid": "k1"}]}
        mock_get.return_value = mock_response
        
        with patch('app.services.keycloak_service.jwt.decode', return_value=payload):
            result = keycloak_service.verify_token("admin-token")
            
            assert Roles.ADMIN in result["roles"]
            assert Roles.USER in result["roles"]
            assert len(result["roles"]) == 2  # System roles filtered


def test_verify_token_flexible_issuer(keycloak_service):
    """Test that token verification accepts multiple issuer formats."""
    # Token with localhost issuer
    payload_localhost = {
        "sub": "user-789",
        "preferred_username": "user",
        "realm_access": {"roles": [Roles.USER]},
        "iss": "http://localhost:8080/realms/rag-realm",
        "exp": 9999999999,
    }
    
    # Token with host.docker.internal issuer
    payload_docker = {
        "sub": "user-789",
        "preferred_username": "user",
        "realm_access": {"roles": [Roles.USER]},
        "iss": "http://host.docker.internal:8080/realms/rag-realm",
        "exp": 9999999999,
    }
    
    with patch('app.services.keycloak_service.httpx.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": []}
        mock_get.return_value = mock_response
        
        with patch('app.services.keycloak_service.jwt.decode') as mock_decode:
            # Test localhost issuer
            mock_decode.return_value = payload_localhost
            result1 = keycloak_service.verify_token("token1")
            assert result1["username"] == "user"
            
            # Test docker issuer
            mock_decode.return_value = payload_docker
            result2 = keycloak_service.verify_token("token2")
            assert result2["username"] == "user"


def test_verify_token_invalid_issuer(keycloak_service):
    """Test that token verification rejects wrong issuer."""
    payload = {
        "sub": "user-999",
        "preferred_username": "hacker",
        "realm_access": {"roles": []},
        "iss": "http://evil.com/realms/wrong-realm",  # Wrong issuer
        "exp": 9999999999,
    }
    
    with patch('app.services.keycloak_service.httpx.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": []}
        mock_get.return_value = mock_response
        
        with patch('app.services.keycloak_service.jwt.decode', return_value=payload):
            with pytest.raises(Exception, match="Invalid token issuer"):
                keycloak_service.verify_token("bad-token")


def test_verify_token_no_roles(keycloak_service):
    """Test token verification when no realm_access roles."""
    payload = {
        "sub": "user-000",
        "preferred_username": "noroles",
        "iss": "http://localhost:8080/realms/rag-realm",
        "exp": 9999999999,
    }
    
    with patch('app.services.keycloak_service.httpx.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": []}
        mock_get.return_value = mock_response
        
        with patch('app.services.keycloak_service.jwt.decode', return_value=payload):
            result = keycloak_service.verify_token("no-roles-token")
            
            assert result["roles"] == []


def test_exchange_credentials_success(keycloak_service):
    """Test successful credential exchange (ROPC)."""
    with patch('app.services.keycloak_service.httpx.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-456",
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response
        
        result = keycloak_service.exchange_credentials("user", "password")
        
        assert result["access_token"] == "access-token-123"
        assert result["refresh_token"] == "refresh-token-456"


def test_exchange_credentials_failure(keycloak_service):
    """Test credential exchange with invalid credentials."""
    with patch('app.services.keycloak_service.httpx.post') as mock_post:
        mock_post.side_effect = Exception("Invalid credentials")
        
        with pytest.raises(Exception):
            keycloak_service.exchange_credentials("wrong", "wrong")


def test_revoke_token_success(keycloak_service):
    """Test successful token revocation."""
    with patch('app.services.keycloak_service.httpx.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response
        
        # Should not raise exception
        keycloak_service.revoke_token("refresh-token", "token-hint")


def test_revoke_token_failure(keycloak_service):
    """Test token revocation handles errors gracefully."""
    with patch('app.services.keycloak_service.httpx.post') as mock_post:
        mock_post.side_effect = Exception("Network error")
        
        # Should not raise exception (revoke is best-effort)
        try:
            keycloak_service.revoke_token("token", "hint")
        except Exception:
            pytest.fail("revoke_token should not raise exceptions")
