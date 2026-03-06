"""Tier validation dependency — NEVER trust frontend tier data.

Usage in routes:
    from app.core.tier_guard import require_tier

    @router.get("/some-pro-feature")
    async def pro_feature(
        current_user: dict = Depends(get_current_user),
        _tier: None = Depends(require_tier("pro")),
    ):
        ...

Tier hierarchy: free < pro < max
- free: basic features only
- pro: OCR, voice, extended quiz, 8 KI-styles
- max: Abitur-Sim, Internet-Recherche, 20 KI-styles, unlimited everything
"""

import logging
from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user
from app.core.database import get_db
import aiosqlite

logger = logging.getLogger(__name__)

TIER_LEVELS = {"free": 0, "pro": 1, "max": 2, "eltern": 1}


def require_tier(min_tier: str):
    """FastAPI dependency that checks user subscription tier from DB.

    NEVER trusts the frontend — always reads tier from the database.
    Returns 403 Forbidden if the user's tier is insufficient.
    """
    min_level = TIER_LEVELS.get(min_tier, 0)

    async def _check_tier(
        current_user: dict = Depends(get_current_user),
        db: aiosqlite.Connection = Depends(get_db),
    ) -> None:
        user_id = current_user["id"]

        # Always fetch tier from DB — never trust the token/frontend
        cursor = await db.execute(
            "SELECT subscription_tier, is_admin FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="User not found")

        row_dict = dict(row)
        user_tier = row_dict.get("subscription_tier", "free") or "free"
        is_admin = bool(row_dict.get("is_admin", 0))

        # Admins always pass
        if is_admin:
            return

        user_level = TIER_LEVELS.get(user_tier, 0)
        if user_level < min_level:
            logger.warning(
                "Tier violation: user=%s has tier=%s, needs=%s for endpoint",
                user_id, user_tier, min_tier,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Diese Funktion erfordert mindestens ein {min_tier.capitalize()}-Abo. "
                       f"Dein aktuelles Abo: {user_tier.capitalize()}.",
            )

    return _check_tier
