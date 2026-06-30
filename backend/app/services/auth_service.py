"""Legacy in-process authentication service (used when Keycloak is not configured).

Passwords are stored as bcrypt hashes — never in plaintext.
Actual credentials must be set via the LEGACY_USERS environment variable as
a JSON string, e.g.:
    LEGACY_USERS='{"admin":"$2b$12$...","demo":"$2b$12$..."}'

A helper to generate a hash:
    python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
"""

import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt

# ---------------------------------------------------------------------------
# User store — loaded from LEGACY_USERS env var (bcrypt hashed passwords).
# Falls back to a safe empty dict; login will fail until env var is set.
# ---------------------------------------------------------------------------
_raw = os.environ.get("LEGACY_USERS", "")
try:
    DEMO_USERS: dict[str, str] = json.loads(_raw) if _raw else {}
except (json.JSONDecodeError, ValueError):
    DEMO_USERS = {}

# Token storage: {token: {username, expires_at}}
ACTIVE_TOKENS: dict[str, dict] = {}

# Token expiry (15 minutes — matches Keycloak access token TTL)
TOKEN_EXPIRY_MINUTES = 15


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate user credentials using bcrypt hash comparison.

    Args:
        username: Username
        password: Plaintext password (compared against stored bcrypt hash)

    Returns:
        True if credentials are valid, False otherwise
    """
    hashed = DEMO_USERS.get(username)
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(username: str) -> str:
    """
    Create a new access token for user.

    Args:
        username: Username to create token for

    Returns:
        Access token string
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES)

    ACTIVE_TOKENS[token] = {
        "username": username,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
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

    if datetime.now(timezone.utc) > token_data["expires_at"]:
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


def cleanup_expired_tokens() -> int:
    """Remove all expired tokens from storage. Returns count of removed tokens."""
    now = datetime.now(timezone.utc)
    expired = [
        token for token, data in ACTIVE_TOKENS.items() if now > data["expires_at"]
    ]
    for token in expired:
        ACTIVE_TOKENS.pop(token, None)
    return len(expired)
