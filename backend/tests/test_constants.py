"""Tests for application constants."""

import pytest

from app.utils.constants import APIMessages, Roles


def test_roles_defined():
    """Test that all required roles are defined."""
    assert hasattr(Roles, "ADMIN")
    assert hasattr(Roles, "USER")
    assert Roles.ADMIN == "admin"
    assert Roles.USER == "user"


def test_roles_all_roles():
    """Test Roles.all_roles() returns all role values."""
    all_roles = Roles.all_roles()

    assert isinstance(all_roles, list)
    assert Roles.ADMIN in all_roles
    assert Roles.USER in all_roles
    assert len(all_roles) == 2


def test_roles_is_valid_role():
    """Test Roles.is_valid_role() validation."""
    assert Roles.is_valid_role(Roles.ADMIN) is True
    assert Roles.is_valid_role(Roles.USER) is True
    assert Roles.is_valid_role("invalid_role") is False
    assert Roles.is_valid_role("") is False
    assert Roles.is_valid_role(None) is False


def test_api_messages_defined():
    """Test that all API messages are defined."""
    assert hasattr(APIMessages, "UNAUTHORIZED")
    assert hasattr(APIMessages, "FORBIDDEN_ADMIN")
    assert hasattr(APIMessages, "FORBIDDEN_USER")
    assert hasattr(APIMessages, "INVALID_CREDENTIALS")
    assert hasattr(APIMessages, "LOGIN_SUCCESS")
    assert hasattr(APIMessages, "LOGOUT_SUCCESS")


def test_api_messages_not_empty():
    """Test that API messages are not empty strings."""
    assert len(APIMessages.UNAUTHORIZED) > 0
    assert len(APIMessages.FORBIDDEN_ADMIN) > 0
    assert len(APIMessages.FORBIDDEN_USER) > 0
    assert len(APIMessages.INVALID_CREDENTIALS) > 0
    assert len(APIMessages.LOGIN_SUCCESS) > 0
    assert len(APIMessages.LOGOUT_SUCCESS) > 0


def test_api_messages_contain_context():
    """Test that API messages contain relevant context."""
    assert "admin" in APIMessages.FORBIDDEN_ADMIN.lower()
    assert (
        "credential" in APIMessages.INVALID_CREDENTIALS.lower()
        or "invalid" in APIMessages.INVALID_CREDENTIALS.lower()
    )
    assert "success" in APIMessages.LOGIN_SUCCESS.lower()
    assert "success" in APIMessages.LOGOUT_SUCCESS.lower()
