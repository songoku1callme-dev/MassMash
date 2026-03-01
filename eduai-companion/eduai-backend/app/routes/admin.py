"""Admin routes: stats dashboard, grant subscriptions, coupon codes, user search.

Admin = user_id=1 OR username='admin' OR email contains 'admin' OR is_admin=1.
"""
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.monitoring import get_monitoring_frontend_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")


async def _is_admin(user: dict, db: aiosqlite.Connection) -> bool:
    """Check if user is an admin."""
    if user.get("id") == 1:
        return True
    if user.get("username", "") == "admin":
        return True
    if "admin" in user.get("email", "").lower():
        return True
    if ADMIN_EMAIL and user.get("email", "") == ADMIN_EMAIL:
        return True
    try:
        cursor = await db.execute(
            "SELECT is_admin FROM users WHERE id = ?", (user["id"],)
        )
        row = await cursor.fetchone()
        if row and dict(row).get("is_admin", 0):
            return True
    except Exception:
        pass
    return False


def _require_admin(is_admin: bool) -> None:
    if not is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren haben Zugriff.")


class GrantSubscriptionRequest(BaseModel):
    user_id: int
    tier: str = "pro"
    duration_days: int = 30


class CreateCouponRequest(BaseModel):
    code: str
    tier: str = "pro"
    duration_days: int = 30
    max_uses: int = 100


@router.get("/is-admin")
async def check_is_admin(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Check if current user is admin."""
    admin = await _is_admin(current_user, db)
    return {"is_admin": admin}


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Return platform statistics for the admin dashboard."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    stats: dict = {}

    cursor = await db.execute("SELECT COUNT(*) FROM users")
    row = await cursor.fetchone()
    stats["total_users"] = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE subscription_tier = 'pro'")
    row = await cursor.fetchone()
    stats["pro_users"] = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE subscription_tier = 'max'")
    row = await cursor.fetchone()
    stats["max_users"] = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM chat_sessions")
    row = await cursor.fetchone()
    stats["total_chat_sessions"] = row[0] if row else 0

    cursor = await db.execute("SELECT COUNT(*) FROM quiz_results")
    row = await cursor.fetchone()
    stats["total_quizzes"] = row[0] if row else 0

    cursor = await db.execute("SELECT AVG(score) FROM quiz_results")
    row = await cursor.fetchone()
    stats["avg_quiz_score"] = round(row[0], 1) if row and row[0] is not None else 0.0

    cursor = await db.execute(
        """SELECT id, username, email, subscription_tier, pro_expires_at, billing_period
        FROM users WHERE subscription_tier != 'free'
        ORDER BY pro_since DESC LIMIT 50"""
    )
    rows = await cursor.fetchall()
    stats["active_subscriptions"] = [dict(r) for r in rows]

    try:
        cursor = await db.execute("SELECT COUNT(*) FROM coupons WHERE is_active = 1")
        row = await cursor.fetchone()
        stats["active_coupons"] = row[0] if row else 0
    except Exception:
        stats["active_coupons"] = 0

    try:
        cursor = await db.execute("SELECT COUNT(*) FROM tournaments")
        row = await cursor.fetchone()
        stats["total_tournaments"] = row[0] if row else 0
    except Exception:
        stats["total_tournaments"] = 0

    cursor = await db.execute(
        "SELECT COUNT(*) FROM activity_log WHERE created_at > datetime('now', '-1 day')"
    )
    row = await cursor.fetchone()
    stats["activity_last_24h"] = row[0] if row else 0

    cursor = await db.execute(
        "SELECT subject, COUNT(*) as cnt FROM chat_sessions GROUP BY subject ORDER BY cnt DESC"
    )
    rows = await cursor.fetchall()
    stats["subject_popularity"] = {row[0]: row[1] for row in rows}

    return stats


@router.get("/search-users")
async def search_users(
    query: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Search users by email or username."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    if not query:
        cursor = await db.execute(
            "SELECT id, username, email, subscription_tier, pro_expires_at, created_at FROM users ORDER BY id DESC LIMIT 50"
        )
    else:
        cursor = await db.execute(
            """SELECT id, username, email, subscription_tier, pro_expires_at, created_at
            FROM users WHERE username LIKE ? OR email LIKE ?
            ORDER BY id DESC LIMIT 50""",
            (f"%{query}%", f"%{query}%"),
        )
    rows = await cursor.fetchall()
    return {"users": [dict(r) for r in rows]}


@router.post("/grant-subscription")
async def grant_subscription(
    req: GrantSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Grant a subscription to a user (admin only)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    if req.duration_days > 0:
        expires_at = (datetime.now() + timedelta(days=req.duration_days)).isoformat()
    else:
        expires_at = ""

    await db.execute(
        """UPDATE users SET subscription_tier = ?, is_pro = 1,
           pro_expires_at = ?, pro_since = datetime('now')
           WHERE id = ?""",
        (req.tier, expires_at, req.user_id),
    )
    await db.commit()

    await db.execute(
        "INSERT INTO admin_logs (admin_id, action, target_user_id, details) VALUES (?, ?, ?, ?)",
        (current_user["id"], "grant_subscription",
         req.user_id, f"tier={req.tier}, days={req.duration_days}"),
    )
    await db.commit()

    return {
        "message": f"Abo {req.tier} f\u00fcr User {req.user_id} aktiviert ({req.duration_days} Tage)",
        "user_id": req.user_id,
        "tier": req.tier,
        "expires_at": expires_at,
    }


@router.post("/create-coupon")
async def create_coupon(
    req: CreateCouponRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new coupon code (admin only)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    code = req.code.strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Code darf nicht leer sein")

    cursor = await db.execute("SELECT id FROM coupons WHERE code = ?", (code,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail=f"Code '{code}' existiert bereits")

    cursor = await db.execute(
        """INSERT INTO coupons (code, tier, duration_days, max_uses, created_by)
        VALUES (?, ?, ?, ?, ?)""",
        (code, req.tier, req.duration_days, req.max_uses, current_user["id"]),
    )
    await db.commit()

    return {
        "message": f"Gutschein '{code}' erstellt",
        "coupon_id": cursor.lastrowid,
        "code": code,
        "tier": req.tier,
        "duration_days": req.duration_days,
        "max_uses": req.max_uses,
    }


@router.get("/coupons")
async def list_coupons(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all coupon codes (admin only)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    cursor = await db.execute("SELECT * FROM coupons ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return {"coupons": [dict(r) for r in rows]}


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Deactivate a coupon (admin only)."""
    admin = await _is_admin(current_user, db)
    _require_admin(admin)

    await db.execute("UPDATE coupons SET is_active = 0 WHERE id = ?", (coupon_id,))
    await db.commit()
    return {"message": "Gutschein deaktiviert"}


@router.post("/redeem-coupon")
async def redeem_coupon(
    code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Redeem a coupon code (any user)."""
    user_id = current_user["id"]
    code = code.strip().upper()

    cursor = await db.execute(
        "SELECT * FROM coupons WHERE code = ? AND is_active = 1", (code,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ung\u00fcltiger oder abgelaufener Gutschein-Code")

    coupon = dict(row)

    if coupon["max_uses"] > 0 and coupon["current_uses"] >= coupon["max_uses"]:
        raise HTTPException(status_code=400, detail="Gutschein wurde bereits zu oft eingel\u00f6st")

    cursor = await db.execute(
        "SELECT id FROM coupon_redemptions WHERE coupon_id = ? AND user_id = ?",
        (coupon["id"], user_id),
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Du hast diesen Gutschein bereits eingel\u00f6st")

    expires_at = (datetime.now() + timedelta(days=coupon["duration_days"])).isoformat()
    await db.execute(
        """UPDATE users SET subscription_tier = ?, is_pro = 1,
           pro_expires_at = ?, pro_since = datetime('now')
           WHERE id = ?""",
        (coupon["tier"], expires_at, user_id),
    )

    await db.execute(
        "INSERT INTO coupon_redemptions (coupon_id, user_id) VALUES (?, ?)",
        (coupon["id"], user_id),
    )
    await db.execute(
        "UPDATE coupons SET current_uses = current_uses + 1 WHERE id = ?",
        (coupon["id"],),
    )
    await db.commit()

    return {
        "message": f"Gutschein eingel\u00f6st! {coupon['tier'].capitalize()}-Abo f\u00fcr {coupon['duration_days']} Tage aktiviert.",
        "tier": coupon["tier"],
        "duration_days": coupon["duration_days"],
        "expires_at": expires_at,
    }


@router.get("/monitoring-config")
async def monitoring_config():
    """Return monitoring configuration for the frontend."""
    return get_monitoring_frontend_config()
