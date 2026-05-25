"""FastAPI dependencies for authentication and authorization."""

import logging
from typing import Optional
from fastapi import Header, HTTPException, Depends

from app.services import auth_service
from app.services.keycloak_service import keycloak_service

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
        roles = ["admin", "user"]
    else:
        roles = ["user"]
    
    return {
        "username": username,
        "sub": username,
        "email": "",
        "roles": roles
    }


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
    
    if "admin" not in user_roles:
        logger.warning(f"Access denied: User {current_user.get('username')} attempted admin action without admin role")
        raise HTTPException(
            status_code=403,
            detail="Admin access required. You do not have permission to perform this action."
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
    
    try:
        token = authorization.replace("Bearer ", "")
        
        if keycloak_service.is_enabled():
            return await keycloak_service.verify_token(token)
        
        username = auth_service.verify_token(token)
        if username:
            roles = ["admin", "user"] if username == "admin" else ["user"]
            return {
                "username": username,
                "sub": username,
                "email": "",
                "roles": roles
            }
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
    
    return None
