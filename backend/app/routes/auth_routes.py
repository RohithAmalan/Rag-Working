"""Authentication routes."""

import logging
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from app.models.auth import LoginRequest, LoginResponse, User
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login endpoint.
    
    Demo credentials:
    - admin / admin123
    - demo / demo123
    - user / user123
    """
    logger.info(f"Login attempt for user: {request.username}")
    
    # Authenticate user
    if not auth_service.authenticate_user(request.username, request.password):
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    # Create access token
    access_token = auth_service.create_access_token(request.username)
    
    logger.info(f"User {request.username} logged in successfully")
    
    return LoginResponse(
        access_token=access_token,
        username=request.username,
        message=f"Welcome back, {request.username}!"
    )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout endpoint - revokes the access token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="No authorization token provided"
        )
    
    token = authorization.replace("Bearer ", "")
    
    # Revoke token
    revoked = auth_service.revoke_token(token)
    
    if revoked:
        logger.info("User logged out successfully")
        return {"message": "Logged out successfully"}
    else:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


@router.get("/verify", response_model=User)
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify token endpoint - checks if current token is valid.
    Returns user info if valid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="No authorization token provided"
        )
    
    token = authorization.replace("Bearer ", "")
    
    # Verify token
    username = auth_service.verify_token(token)
    
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    
    return User(username=username, is_active=True)


@router.get("/cleanup")
async def cleanup_tokens():
    """Admin endpoint to cleanup expired tokens."""
    count = auth_service.cleanup_expired_tokens()
    return {"message": f"Cleaned up {count} expired tokens"}
