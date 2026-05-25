"""Tests for authentication and authorization dependencies."""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch, MagicMock

from app.utils.dependencies import (
    get_current_user,
    require_admin,
    require_user,
    get_current_user_optional,
)
from app.utils.constants import Roles, APIMessages


@pytest.mark.asyncio
async def test_get_current_user_no_token():
    """Test get_current_user without authorization header."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)
    
    assert exc_info.value.status_code == 401
    assert "Authorization header missing" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_current_user_invalid_format():
    """Test get_current_user with invalid token format."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization="InvalidFormat")
    
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@patch('app.utils.dependencies.keycloak_service')
async def test_get_current_user_keycloak_success(mock_keycloak):
    """Test get_current_user with valid Keycloak token."""
    mock_keycloak.verify_token.return_value = {
        "username": "testuser",
        "sub": "user-123",
        "email": "test@example.com",
        "roles": [Roles.USER],
    }
    
    result = await get_current_user(authorization="Bearer valid-keycloak-token")
    
    assert result["username"] == "testuser"
    assert result["sub"] == "user-123"
    assert Roles.USER in result["roles"]
    mock_keycloak.verify_token.assert_called_once_with("valid-keycloak-token")


@pytest.mark.asyncio
@patch('app.utils.dependencies.keycloak_service')
@patch('app.utils.dependencies.auth_service')
async def test_get_current_user_fallback_to_legacy(mock_auth, mock_keycloak):
    """Test get_current_user falls back to legacy auth when Keycloak fails."""
    mock_keycloak.verify_token.side_effect = Exception("Keycloak error")
    mock_auth.verify_token.return_value = {
        "username": "admin",
        "roles": [Roles.ADMIN, Roles.USER],
    }
    
    result = await get_current_user(authorization="Bearer legacy-token")
    
    assert result["username"] == "admin"
    assert Roles.ADMIN in result["roles"]
    mock_auth.verify_token.assert_called_once_with("legacy-token")


@pytest.mark.asyncio
async def test_require_admin_success():
    """Test require_admin allows admin users."""
    admin_user = {
        "username": "admin",
        "roles": [Roles.ADMIN, Roles.USER],
    }
    
    result = await require_admin(current_user=admin_user)
    
    assert result == admin_user


@pytest.mark.asyncio
async def test_require_admin_forbidden():
    """Test require_admin blocks non-admin users."""
    regular_user = {
        "username": "user",
        "roles": [Roles.USER],
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=regular_user)
    
    assert exc_info.value.status_code == 403
    assert APIMessages.FORBIDDEN_ADMIN in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_admin_no_roles():
    """Test require_admin blocks users without roles."""
    user_no_roles = {
        "username": "user",
        "roles": [],
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=user_no_roles)
    
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_user_success():
    """Test require_user allows authenticated users."""
    regular_user = {
        "username": "user",
        "roles": [Roles.USER],
    }
    
    result = await require_user(current_user=regular_user)
    
    assert result == regular_user


@pytest.mark.asyncio
async def test_get_current_user_optional_with_token():
    """Test get_current_user_optional returns user info when token present."""
    with patch('app.utils.dependencies.keycloak_service') as mock_keycloak:
        mock_keycloak.verify_token.return_value = {
            "username": "testuser",
            "roles": [Roles.USER],
        }
        
        result = await get_current_user_optional(authorization="Bearer token")
        
        assert result is not None
        assert result["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_current_user_optional_no_token():
    """Test get_current_user_optional returns None when no token."""
    result = await get_current_user_optional(authorization=None)
    
    assert result is None


@pytest.mark.asyncio
async def test_get_current_user_optional_invalid_token():
    """Test get_current_user_optional returns None when token invalid."""
    with patch('app.utils.dependencies.keycloak_service') as mock_keycloak:
        mock_keycloak.verify_token.side_effect = Exception("Invalid token")
        
        with patch('app.utils.dependencies.auth_service') as mock_auth:
            mock_auth.verify_token.side_effect = Exception("Invalid token")
            
            result = await get_current_user_optional(authorization="Bearer bad-token")
            
            assert result is None
