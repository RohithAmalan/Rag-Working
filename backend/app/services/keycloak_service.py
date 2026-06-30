"""Keycloak integration service — JWKS JWT validation and ROPC token exchange."""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx
from app.utils.config import settings
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


class KeycloakService:
    """
    Handles Keycloak identity operations:
    - Validate access tokens using JWKS (public key from Keycloak)
    - Exchange username/password for tokens via ROPC grant
    - Revoke tokens on logout
    """

    def __init__(self) -> None:
        self._jwks_cache: dict | None = None
        self._jwks_fetched_at: float = 0
        self._cache_ttl: int = 300  # refresh JWKS every 5 minutes

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        return f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"

    @property
    def jwks_url(self) -> str:
        return f"{self.base_url}/protocol/openid-connect/certs"

    @property
    def token_url(self) -> str:
        return f"{self.base_url}/protocol/openid-connect/token"

    @property
    def logout_url(self) -> str:
        return f"{self.base_url}/protocol/openid-connect/logout"

    # ------------------------------------------------------------------
    # JWKS caching
    # ------------------------------------------------------------------

    async def _get_jwks(self) -> dict:
        now = time.monotonic()
        if self._jwks_cache and (now - self._jwks_fetched_at) < self._cache_ttl:
            return self._jwks_cache

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(self.jwks_url)
            resp.raise_for_status()
            self._jwks_cache = resp.json()
            self._jwks_fetched_at = now
            logger.debug("JWKS refreshed from Keycloak")
            return self._jwks_cache

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        """Return True when Keycloak is configured via environment variables."""
        return bool(
            settings.keycloak_url
            and settings.keycloak_realm
            and settings.keycloak_client_id
        )

    async def verify_token(self, token: str) -> Optional[dict]:
        """
        Validate a Keycloak access token using the realm's public key (JWKS).

        Returns a user-info dict on success:
            {"username": str, "sub": str, "email": str, "roles": list[str]}
        Returns None if the token is invalid or Keycloak is unreachable.
        """
        try:
            jwks = await self._get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                # Audience validation is skipped — public clients may have
                # aud="account" by default; issuer is verified manually below.
                options={"verify_aud": False},
            )

            # Flexible issuer validation: accept both localhost and host.docker.internal
            # This handles the case where frontend (localhost) and backend (Docker) use different URLs
            token_issuer = payload.get("iss", "")
            expected_realm = f"/realms/{settings.keycloak_realm}"
            if not token_issuer.endswith(expected_realm):
                logger.warning(
                    "JWT issuer mismatch: %s (expected realm: %s)",
                    token_issuer,
                    expected_realm,
                )
                return None

            return {
                "username": payload.get("preferred_username") or payload.get("sub", ""),
                "sub": payload.get("sub"),
                "email": payload.get("email", ""),
                "roles": payload.get("realm_access", {}).get("roles", []),
            }
        except JWTError as exc:
            logger.warning("JWT validation failed: %s", exc)
            return None
        except Exception as exc:
            logger.error("Keycloak verify_token error: %s", exc)
            return None

    async def exchange_credentials(
        self, username: str, password: str
    ) -> Optional[dict]:
        """
        Exchange username/password for Keycloak tokens using the Resource Owner
        Password Credentials (ROPC) grant.

        Returns the full token response (access_token, refresh_token, etc.)
        or None on failure.

        Note: ROPC is supported by Keycloak for trusted first-party apps but
        is deprecated in OAuth 2.1. Use the SSO redirect flow for new clients.
        """
        data = {
            "grant_type": "password",
            "client_id": settings.keycloak_client_id,
            "username": username,
            "password": password,
            "scope": "openid profile email",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.token_url, data=data)
                if resp.status_code == 200:
                    return resp.json()
                body = resp.json()
                logger.warning(
                    "Keycloak ROPC failed [%s]: %s",
                    resp.status_code,
                    body.get("error_description", body),
                )
                return None
        except Exception as exc:
            logger.error("Keycloak exchange_credentials error: %s", exc)
            return None

    async def revoke_token(self, refresh_token: str) -> bool:
        """Logout by revoking the refresh token via Keycloak's logout endpoint."""
        data = {
            "client_id": settings.keycloak_client_id,
            "refresh_token": refresh_token,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.logout_url, data=data)
                return resp.status_code in (200, 204)
        except Exception as exc:
            logger.error("Keycloak revoke_token error: %s", exc)
            return False


# Module-level singleton
keycloak_service = KeycloakService()
