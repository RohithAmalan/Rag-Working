"""FastAPI dependencies for authentication and authorization."""

import logging
from typing import Optional, List
from fastapi import Header, HTTPException, Depends

from app.services import auth_service
from app.services.keycloak_service import keycloak_service
from app.utils.constants import Roles, APIMessages

logger = logging.getLogger(__name__)


def _legacy_user_dict(username: str) -> dict:
    """
    Build a user info dict for the legacy (non-Keycloak) auth path.
    Centralises the role-assignment logic so it cannot diverge between
    get_current_user, get_current_user_optional, and auth_routes.py.
    """
    roles = [Roles.ADMIN, Roles.USER] if username == "admin" else [Roles.USER]
    return {
        "username": username,
        "sub": username,
        "email": "",
        "roles": roles,
    }


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Extract and verify the current user from the Authorization header.

    Returns:
        dict: User information including username, sub, email, and roles

    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No authorization token provided")

    token = authorization.replace("Bearer ", "")

    if keycloak_service.is_enabled():
        user_info = await keycloak_service.verify_token(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_info

    username = auth_service.verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return _legacy_user_dict(username)


async def require_role(required_role: str, user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to check if user has a specific role.

    Raises:
        HTTPException: 403 if user lacks the required role
    """
    user_roles = user.get("roles", [])
    if required_role not in user_roles:
        logger.warning(
            "User %s denied: requires %s, has %s",
            user.get("username"), required_role, user_roles,
        )
        raise HTTPException(status_code=403, detail=f"Access denied: requires {required_role} role")
    return user


async def require_any_role(required_roles: List[str], user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to check if user has any of the required roles.

    Raises:
        HTTPException: 403 if user lacks all required roles
    """
    user_roles = user.get("roles", [])
    if not any(role in user_roles for role in required_roles):
        logger.warning(
            "User %s denied: requires one of %s, has %s",
            user.get("username"), required_roles, user_roles,
        )
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: requires one of {required_roles} roles",
        )
    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require admin role for endpoint access.

    Raises:
        HTTPException: 403 if user doesn't have admin role
    """
    user_roles = current_user.get("roles", [])

    if Roles.ADMIN not in user_roles:
        logger.warning(
            "Access denied: User %s attempted admin action without admin role",
            current_user.get("username"),
        )
        raise HTTPException(status_code=403, detail=APIMessages.FORBIDDEN_ADMIN)

    logger.info("Admin access granted to user: %s", current_user.get("username"))
    return current_user


async def require_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require any authenticated user.
    Explicitly marks endpoints that need authentication without role restriction.
    """
    return current_user


async def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Extract user info if token is present, but don't require it.
    Useful for endpoints that behave differently based on auth state.

    Returns:
        dict or None: User information if authenticated, None otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    if keycloak_service.is_enabled():
        return await keycloak_service.verify_token(token)

    username = auth_service.verify_token(token)
    if not username:
        return None

    return _legacy_user_dict(username)
