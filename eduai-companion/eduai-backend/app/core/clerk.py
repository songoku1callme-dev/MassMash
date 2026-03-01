"""Clerk OAuth integration scaffolding.

This module provides Clerk JWT verification for the backend.
Activate by setting CLERK_SECRET_KEY in environment variables.

When active, the frontend uses @clerk/clerk-react for login/signup,
and this module verifies the Clerk-issued JWT on protected routes.

Docs: https://clerk.com/docs/backend-requests/handling/manual-jwt
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")

# Set to True when both keys are present
CLERK_ENABLED = bool(CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY)

if CLERK_ENABLED:
    logger.info("Clerk OAuth is ENABLED.")
else:
    logger.info("Clerk OAuth is DISABLED (keys not set). Using built-in JWT auth.")


async def verify_clerk_token(token: str) -> Optional[dict]:
    """Verify a Clerk-issued session JWT and return user claims.

    Returns None if verification fails or Clerk is not configured.

    The returned dict contains at minimum:
        - sub: Clerk user ID (e.g. "user_2abc...")
        - email: user email
        - name: full name (if available)

    Usage:
        from app.core.clerk import verify_clerk_token, CLERK_ENABLED

        if CLERK_ENABLED:
            claims = await verify_clerk_token(bearer_token)
            if claims is None:
                raise HTTPException(401)
            user_id = claims["sub"]
    """
    if not CLERK_ENABLED:
        return None

    # NOTE: Full implementation requires the `pyjwt` or `jose` library
    # to verify the RS256 JWT against Clerk's JWKS endpoint.
    # The JWKS URL is: https://<your-clerk-domain>/.well-known/jwks.json
    #
    # Skeleton implementation below — uncomment and complete when keys are set.
    #
    # from jose import jwt, JWTError
    # import httpx
    #
    # CLERK_JWKS_URL = f"https://api.clerk.com/v1/jwks"
    # headers = {"Authorization": f"Bearer {CLERK_SECRET_KEY}"}
    #
    # async with httpx.AsyncClient() as client:
    #     resp = await client.get(CLERK_JWKS_URL, headers=headers)
    #     jwks = resp.json()
    #
    # try:
    #     payload = jwt.decode(
    #         token,
    #         jwks,
    #         algorithms=["RS256"],
    #         options={"verify_aud": False},
    #     )
    #     return {
    #         "sub": payload.get("sub"),
    #         "email": payload.get("email", ""),
    #         "name": payload.get("name", ""),
    #     }
    # except JWTError:
    #     return None

    logger.warning("Clerk token verification called but not fully implemented yet.")
    return None


def get_clerk_frontend_config() -> dict:
    """Return Clerk config for the frontend (safe to expose)."""
    return {
        "enabled": CLERK_ENABLED,
        "publishable_key": CLERK_PUBLISHABLE_KEY if CLERK_ENABLED else "",
    }
