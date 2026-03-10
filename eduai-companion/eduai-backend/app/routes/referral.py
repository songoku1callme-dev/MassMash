"""Referral system: invite friends, both get 7 days Pro."""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/referral", tags=["referral"])


async def _ensure_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER,
            code TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            redeemed_at TEXT,
            FOREIGN KEY (referrer_id) REFERENCES users(id),
            FOREIGN KEY (referred_id) REFERENCES users(id)
        )
    """)
    await db.commit()


@router.get("/code")
async def get_referral_code(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get or create a referral code for the current user."""
    await _ensure_tables(db)
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT code FROM referrals WHERE referrer_id = ? AND referred_id IS NULL LIMIT 1",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row:
        code = dict(row)["code"]
    else:
        code = f"edu-{secrets.token_urlsafe(6)}"
        await db.execute(
            "INSERT INTO referrals (referrer_id, code) VALUES (?, ?)",
            (user_id, code),
        )
        await db.commit()

    username = current_user.get("username", "user")
    return {
        "code": code,
        "link": f"https://lumnos.de/ref/{code}",
        "share_text": f"Lerne mit Lumnos! Nutze meinen Code '{code}' und wir bekommen beide 7 Tage Pro gratis!",
    }


@router.post("/redeem/{code}")
async def redeem_referral(
    code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Redeem a referral code."""
    await _ensure_tables(db)
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT * FROM referrals WHERE code = ? AND status = 'pending'",
        (code,),
    )
    referral = await cursor.fetchone()
    if not referral:
        raise HTTPException(status_code=404, detail="Ungültiger oder bereits eingelöster Code")

    ref_dict = dict(referral)
    if ref_dict["referrer_id"] == user_id:
        raise HTTPException(status_code=400, detail="Du kannst deinen eigenen Code nicht einlösen")

    # Check if user already redeemed a code
    cursor = await db.execute(
        "SELECT id FROM referrals WHERE referred_id = ? AND status = 'redeemed'",
        (user_id,),
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Du hast bereits einen Referral-Code eingelöst")

    # Grant 7 days Pro to both users
    pro_until = (datetime.now() + timedelta(days=7)).isoformat()

    await db.execute(
        "UPDATE users SET subscription_tier = 'pro', is_pro = 1, pro_expires_at = ? WHERE id = ? AND subscription_tier = 'free'",
        (pro_until, user_id),
    )
    await db.execute(
        "UPDATE users SET subscription_tier = 'pro', is_pro = 1, pro_expires_at = ? WHERE id = ? AND subscription_tier = 'free'",
        (pro_until, ref_dict["referrer_id"]),
    )

    await db.execute(
        "UPDATE referrals SET referred_id = ?, status = 'redeemed', redeemed_at = datetime('now') WHERE id = ?",
        (user_id, ref_dict["id"]),
    )

    # Create a new code for the referrer
    new_code = f"edu-{secrets.token_urlsafe(6)}"
    await db.execute(
        "INSERT INTO referrals (referrer_id, code) VALUES (?, ?)",
        (ref_dict["referrer_id"], new_code),
    )
    await db.commit()

    return {"status": "redeemed", "bonus": "7 Tage Pro gratis für beide!"}


@router.get("/stats")
async def referral_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get referral statistics."""
    await _ensure_tables(db)
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ? AND status = 'redeemed'",
        (user_id,),
    )
    redeemed = dict(await cursor.fetchone())["cnt"]

    return {
        "total_referrals": redeemed,
        "bonus_days_earned": redeemed * 7,
    }
