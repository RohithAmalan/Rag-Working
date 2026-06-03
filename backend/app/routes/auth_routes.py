"""Authentication routes — supports both Keycloak and legacy in-memory auth."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, Response
from typing import Optional
from jose import jwt as jose_jwt

from app.models.auth import LoginRequest, LoginResponse, User
from app.services import auth_service
from app.services.keycloak_service import keycloak_service
from app.utils.constants import Roles, APIMessages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# In Keycloak mode, access tokens are stateless JWTs. Keep a small in-memory
# denylist so explicit logout can invalidate current tokens for this process.
REVOKED_KEYCLOAK_TOKENS = {}


def _cleanup_revoked_keycloak_tokens() -> int:
    now_ts = datetime.now(timezone.utc).timestamp()
    expired = [token for token, exp in REVOKED_KEYCLOAK_TOKENS.items() if exp <= now_ts]
    for token in expired:
        REVOKED_KEYCLOAK_TOKENS.pop(token, None)
    return len(expired)


def _revoke_keycloak_access_token(token: str) -> None:
    # Store token until its exp so verify can reject it post-logout.
    try:
        claims = jose_jwt.get_unverified_claims(token)
        exp = float(claims.get("exp", datetime.now(timezone.utc).timestamp() + 3600))
    except Exception:
        exp = datetime.now(timezone.utc).timestamp() + 3600
    REVOKED_KEYCLOAK_TOKENS[token] = exp


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """
    Login endpoint.

    When Keycloak is configured (KEYCLOAK_URL env var set) credentials are
    forwarded to Keycloak via the ROPC grant and a real JWT is returned.

    Fallback demo credentials (no Keycloak):
    - admin / admin123
    - demo / demo123
    - user / user123
    
    Refresh token is set as an HttpOnly, Secure, SameSite cookie for secure refresh flows.
    """
    logger.info(f"Login attempt for user: {request.username}")

    if keycloak_service.is_enabled():
        tokens = await keycloak_service.exchange_credentials(request.username, request.password)
        if not tokens:
            logger.warning(f"Keycloak login failed for user: {request.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Extract roles from the access token
        user_info = await keycloak_service.verify_token(tokens["access_token"])
        roles = user_info.get("roles", []) if user_info else []
        
        # Set refresh token as HttpOnly cookie (secure token storage)
        if tokens.get("refresh_token"):
            response.set_cookie(
                key="refresh_token",
                value=tokens["refresh_token"],
                httponly=True,
                secure=True,  # Only send over HTTPS in production
                samesite="lax",
                max_age=86400 * 7,  # 7 days
            )
        
        logger.info(f"User {request.username} authenticated via Keycloak with roles: {roles}")
        return LoginResponse(
            access_token=tokens["access_token"],
            refresh_token=None,  # Don't expose refresh token in body; it's in the cookie
            token_type="bearer",
            username=request.username,
            roles=roles,
            message=f"Welcome back, {request.username}!",
        )

    # --- Legacy in-memory auth (no Keycloak) ---
    if not auth_service.authenticate_user(request.username, request.password):
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Assign default roles for legacy auth
    roles = [Roles.ADMIN, Roles.USER] if request.username == "admin" else [Roles.USER]
    
    access_token = auth_service.create_access_token(request.username)
    logger.info(f"User {request.username} logged in via legacy auth with roles: {roles}")
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        username=request.username,
        roles=roles,
        message=f"Welcome back, {request.username}!",
    )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None), refresh_token: Optional[str] = None):
    """
    Logout endpoint.

    When Keycloak is active the refresh_token body field is used to revoke
    the session.  Pass it as a JSON body: {"refresh_token": "<rt>"}.

    Falls back to legacy in-memory token revocation otherwise.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No authorization token provided")

    token = authorization.replace("Bearer ", "")

    if keycloak_service.is_enabled():
        # Reject malformed/expired access tokens instead of treating them as
        # successful local logout requests.
        user_info = await keycloak_service.verify_token(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Always locally revoke the presented access token so subsequent verify
        # calls fail even if no refresh token is provided by the client.
        _revoke_keycloak_access_token(token)

        if refresh_token:
            revoked = await keycloak_service.revoke_token(refresh_token)
            if revoked:
                logger.info("User logged out via Keycloak (server + local revoke)")
                return {"message": "Logged out successfully"}
            raise HTTPException(status_code=401, detail="Logout failed — invalid refresh token")

        logger.info("User logged out via Keycloak (local revoke only)")
        return {"message": "Logged out successfully"}

    # Legacy path
    revoked = auth_service.revoke_token(token)
    if revoked:
        logger.info("User logged out via legacy auth")
        return {"message": "Logged out successfully"}

    raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/verify", response_model=User)
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify the current Bearer token.

    Returns user info (username, roles) if valid.
    Validates against Keycloak JWKS when Keycloak is configured.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No authorization token provided")

    token = authorization.replace("Bearer ", "")

    if keycloak_service.is_enabled():
        _cleanup_revoked_keycloak_tokens()
        if token in REVOKED_KEYCLOAK_TOKENS:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user_info = await keycloak_service.verify_token(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return User(
            username=user_info["username"],
            roles=user_info.get("roles", []),
            is_active=True
        )

    # Legacy path
    username = auth_service.verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Assign default roles for legacy auth
    roles = [Roles.ADMIN, Roles.USER] if username == "admin" else [Roles.USER]
    
    return User(username=username, roles=roles, is_active=True)


@router.get("/cleanup")
async def cleanup_tokens():
    """Admin endpoint to clean up expired legacy tokens (no-op when Keycloak is active)."""
    legacy_count = auth_service.cleanup_expired_tokens()
    revoked_count = _cleanup_revoked_keycloak_tokens()
    total = legacy_count + revoked_count
    return {"message": f"Cleaned up {total} expired tokens"}
