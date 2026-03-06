"""Clerk OAuth integration.

Verifies Clerk-issued JWTs using the JWKS endpoint (RS256).
Activate by setting CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY in environment.

Docs: https://clerk.com/docs/backend-requests/handling/manual-jwt
"""

import os
import logging
from typing import Optional

from jose import jwt, JWTError
import httpx

logger = logging.getLogger(__name__)

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")

# Set to True when both keys are present
CLERK_ENABLED = bool(CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY)

if CLERK_ENABLED:
    logger.info("Clerk OAuth is ENABLED.")
else:
    logger.info("Clerk OAuth is DISABLED (keys not set). Using built-in JWT auth.")

# Cache the JWKS keys to avoid fetching on every request
_jwks_cache: Optional[dict] = None


async def _get_jwks() -> dict:
    """Fetch JWKS from Clerk's API (cached after first call)."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = "https://api.clerk.com/v1/jwks"
    headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url, headers=headers)
        if resp.status_code == 200:
            _jwks_cache = resp.json()
            return _jwks_cache
        else:
            logger.error("Failed to fetch Clerk JWKS: %s %s", resp.status_code, resp.text)
            return {"keys": []}


async def verify_clerk_token(token: str) -> Optional[dict]:
    """Verify a Clerk-issued session JWT and return user claims.

    Returns None if verification fails or Clerk is not configured.

    The returned dict contains:
        - sub: Clerk user ID (e.g. "user_2abc...")
        - email: user email
        - name: full name (if available)
        - image_url: profile photo URL
    """
    if not CLERK_ENABLED:
        return None

    try:
        jwks_data = await _get_jwks()
        keys = jwks_data.get("keys", [])
        if not keys:
            logger.error("No JWKS keys available from Clerk")
            return None

        # Find the matching key by kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        rsa_key = None
        for key in keys:
            if key.get("kid") == kid:
                rsa_key = key
                break

        if rsa_key is None and keys:
            rsa_key = keys[0]

        if rsa_key is None:
            return None

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        return {
            "sub": payload.get("sub", ""),
            "email": payload.get("email", payload.get("primary_email", "")),
            "name": payload.get("name", payload.get("full_name", "")),
            "image_url": payload.get("image_url", ""),
        }

    except JWTError as e:
        logger.warning("Clerk JWT verification failed: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error verifying Clerk token: %s", e)
        return None


def invalidate_jwks_cache():
    """Clear the JWKS cache (useful if keys are rotated)."""
    global _jwks_cache
    _jwks_cache = None


def get_clerk_frontend_config() -> dict:
    """Return Clerk config for the frontend (safe to expose).

    Reads env vars at request time so that test fixtures can override them.
    """
    secret = os.getenv("CLERK_SECRET_KEY", "")
    pub = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    enabled = bool(secret and pub)
    return {
        "enabled": enabled,
        "publishable_key": pub if enabled else "",
    }
