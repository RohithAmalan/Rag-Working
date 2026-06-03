"""FastAPI dependencies for authentication and authorization."""

import logging
from typing import Optional, List
from fastapi import Header, HTTPException, Depends

from app.services import auth_service
from app.services.keycloak_service import keycloak_service
from app.utils.constants import Roles, APIMessages

logger = logging.getLogger(__name__)


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
    
    # Keycloak path - returns full user info with roles
    if keycloak_service.is_enabled():
        user_info = await keycloak_service.verify_token(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_info
    
    # Legacy path - basic username only
    username = auth_service.verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # For legacy auth, assign default roles based on username
    roles = []
    if username == "admin":
        roles = [Roles.ADMIN, Roles.USER]
    else:
        roles = [Roles.USER]
    
    return {
        "username": username,
        "sub": username,
        "email": "",
        "roles": roles,
    }


async def require_role(required_role: str, user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to check if user has a specific role.
    
    Args:
        required_role: The role required (e.g., Roles.ADMIN)
        user: Current authenticated user (auto-injected)
        
    Returns:
        dict: User info if authorized
        
    Raises:
        HTTPException: 403 if user lacks the required role
    """
    user_roles = user.get("roles", [])
    if required_role not in user_roles:
        logger.warning(f"User {user.get('username')} denied: requires {required_role}, has {user_roles}")
        raise HTTPException(status_code=403, detail=f"Access denied: requires {required_role} role")
    return user


async def require_any_role(required_roles: List[str], user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to check if user has any of the required roles.
    
    Args:
        required_roles: List of roles (user needs at least one)
        user: Current authenticated user (auto-injected)
        
    Returns:
        dict: User info if authorized
        
    Raises:
        HTTPException: 403 if user lacks all required roles
    """
    user_roles = user.get("roles", [])
    if not any(role in user_roles for role in required_roles):
        logger.warning(f"User {user.get('username')} denied: requires one of {required_roles}, has {user_roles}")
        raise HTTPException(status_code=403, detail=f"Access denied: requires one of {required_roles} roles")
    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require admin role for endpoint access.
    
    Args:
        current_user: Current user info from get_current_user
        
    Returns:
        dict: User information if admin
        
    Raises:
        HTTPException: 403 if user doesn't have admin role
    """
    user_roles = current_user.get("roles", [])
    
    if Roles.ADMIN not in user_roles:
        logger.warning(f"Access denied: User {current_user.get('username')} attempted admin action without admin role")
        raise HTTPException(
            status_code=403,
            detail=APIMessages.FORBIDDEN_ADMIN
        )
    
    logger.info(f"Admin access granted to user: {current_user.get('username')}")
    return current_user


async def require_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Require user role for endpoint access (any authenticated user).
    
    Args:
        current_user: Current user info from get_current_user
        
    Returns:
        dict: User information
    """
    # Anyone with valid authentication can access
    # This is useful for explicitly marking endpoints that need authentication
    return current_user


async def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Extract user info if token is present, but don't require it.
    Useful for endpoints that work differently based on auth state.
    
    Returns:
        dict or None: User information if authenticated, None otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    
    # Keycloak path
    if keycloak_service.is_enabled():
        user_info = await keycloak_service.verify_token(token)
        return user_info
    
    # Legacy path
    username = auth_service.verify_token(token)
    if not username:
        return None
    
    # For legacy auth, assign default roles based on username
    roles = []
    if username == "admin":
        roles = [Roles.ADMIN, Roles.USER]
    else:
        roles = [Roles.USER]
    
    return {
        "username": username,
        "sub": username,
        "email": "",
        "roles": roles,
    }
