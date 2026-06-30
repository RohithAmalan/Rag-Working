"""Simple authentication service with in-memory user storage."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

# Simple in-memory storage for demo purposes
# In production, use a database with hashed passwords
DEMO_USERS = {
    "admin": "admin123",  # username: password
    "demo": "demo123",
    "user": "user123",
}

# Token storage: {token: {username, expires_at}}
ACTIVE_TOKENS: dict[str, dict] = {}

# Token expiry (24 hours)
TOKEN_EXPIRY_HOURS = 24


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate user credentials.

    Args:
        username: Username
        password: Password

    Returns:
        True if credentials are valid, False otherwise
    """
    return DEMO_USERS.get(username) == password


def create_access_token(username: str) -> str:
    """
    Create a new access token for user.

    Args:
        username: Username to create token for

    Returns:
        Access token string
    """
    # Generate secure random token
    token = secrets.token_urlsafe(32)

    # Calculate expiry time
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)

    # Store token
    ACTIVE_TOKENS[token] = {
        "username": username,
        "expires_at": expires_at,
        "created_at": datetime.utcnow(),
    }

    return token


def verify_token(token: str) -> Optional[str]:
    """
    Verify access token and return username if valid.

    Args:
        token: Access token to verify

    Returns:
        Username if token is valid, None otherwise
    """
    token_data = ACTIVE_TOKENS.get(token)

    if not token_data:
        return None

    # Check if token expired
    if datetime.utcnow() > token_data["expires_at"]:
        # Remove expired token
        ACTIVE_TOKENS.pop(token, None)
        return None

    return token_data["username"]


def revoke_token(token: str) -> bool:
    """
    Revoke (logout) an access token.

    Args:
        token: Access token to revoke

    Returns:
        True if token was revoked, False if token didn't exist
    """
    if token in ACTIVE_TOKENS:
        ACTIVE_TOKENS.pop(token)
        return True
    return False


def cleanup_expired_tokens():
    """Remove all expired tokens from storage."""
    now = datetime.utcnow()
    expired = [
        token for token, data in ACTIVE_TOKENS.items() if now > data["expires_at"]
    ]
    for token in expired:
        ACTIVE_TOKENS.pop(token, None)
    return len(expired)
