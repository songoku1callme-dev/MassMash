"""Pomodoro Lern-Timer routes.

Supreme 9.0 Phase 8: 25 Min lernen, 5 Min Pause, XP pro Pomodoro.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pomodoro", tags=["pomodoro"])


@router.post("/complete")
async def complete_pomodoro(
    subject: str = "general",
    duration_minutes: int = 25,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Log a completed Pomodoro session and award XP."""
    user_id = current_user["id"]

    # Log activity
    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, subject, description, metadata)
        VALUES (?, 'pomodoro', ?, ?, ?)""",
        (user_id, subject, f"Pomodoro abgeschlossen: {duration_minutes} Min",
         json.dumps({"duration": duration_minutes})),
    )
    await db.commit()

    # Award XP
    xp_earned = 25
    try:
        from app.routes.gamification import add_xp
        await add_xp(user_id, xp_earned, "pomodoro", db)
    except Exception:
        pass

    return {"message": "Pomodoro abgeschlossen!", "xp_earned": xp_earned, "duration": duration_minutes}


@router.get("/stats")
async def pomodoro_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get Pomodoro statistics for the current user."""
    user_id = current_user["id"]

    # Today's pomodoros
    cursor = await db.execute(
        """SELECT COUNT(*) as cnt FROM activity_log
        WHERE user_id = ? AND activity_type = 'pomodoro' AND date(created_at) = date('now')""",
        (user_id,),
    )
    row = await cursor.fetchone()
    today = dict(row)["cnt"] if row else 0

    # This week's pomodoros
    cursor = await db.execute(
        """SELECT COUNT(*) as cnt FROM activity_log
        WHERE user_id = ? AND activity_type = 'pomodoro'
        AND created_at >= datetime('now', '-7 days')""",
        (user_id,),
    )
    row = await cursor.fetchone()
    week = dict(row)["cnt"] if row else 0

    # All time
    cursor = await db.execute(
        """SELECT COUNT(*) as cnt FROM activity_log
        WHERE user_id = ? AND activity_type = 'pomodoro'""",
        (user_id,),
    )
    row = await cursor.fetchone()
    total = dict(row)["cnt"] if row else 0

    return {
        "today": today,
        "today_minutes": today * 25,
        "week": week,
        "week_minutes": week * 25,
        "total": total,
        "total_minutes": total * 25,
    }
