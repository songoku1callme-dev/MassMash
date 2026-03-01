"""Taegliche Quests routes - Gamification 2.0.

Supreme 10.0 Phase 6: Daily quests with progress tracking.
"""
import json
import logging
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quests", tags=["quests"])


def _generate_daily_quests(user_stats: dict) -> list[dict]:
    """Generate 3 daily quests based on user profile."""
    today = date.today().isoformat()
    quests = []

    # Quest 1: Practice weak subject
    weak = user_stats.get("weak_subject", "Mathematik")
    quests.append({
        "quest_id": f"weak_{today}",
        "title": f"Uebe {weak}",
        "description": f"Mache ein Quiz ueber {weak}",
        "xp_reward": 50,
        "target": 1,
        "icon": "target",
        "type": "quiz",
    })

    # Quest 2: Maintain streak
    quests.append({
        "quest_id": f"streak_{today}",
        "title": "Streak am Leben halten",
        "description": "Lerne heute mindestens 15 Minuten",
        "xp_reward": 30,
        "target": 1,
        "icon": "flame",
        "type": "time",
    })

    # Quest 3: Social / multiplayer
    quests.append({
        "quest_id": f"social_{today}",
        "title": "Duell gewinnen",
        "description": "Gewinne ein Multiplayer-Quiz oder chatte in einer Gruppe",
        "xp_reward": 75,
        "target": 1,
        "icon": "swords",
        "type": "social",
    })

    return quests


@router.get("/today")
async def get_daily_quests(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get today's quests for the current user."""
    user_id = current_user["id"]
    today = date.today().isoformat()

    # Check if quests already exist for today
    cursor = await db.execute(
        "SELECT * FROM daily_quests WHERE user_id = ? AND quest_date = ?",
        (user_id, today),
    )
    existing = await cursor.fetchall()

    if existing:
        quests = []
        for row in existing:
            rd = dict(row)
            quests.append({
                "quest_id": rd["quest_id"],
                "title": rd["title"],
                "description": rd["description"],
                "xp_reward": rd["xp_reward"],
                "target": rd["target"],
                "progress": rd["progress"],
                "completed": bool(rd["completed"]),
            })
        return {"quests": quests, "date": today}

    # Generate new quests
    # Get user's weak subject
    weak_cursor = await db.execute(
        """SELECT subject FROM user_memories
        WHERE user_id = ? AND schwach = 1
        GROUP BY subject ORDER BY COUNT(*) DESC LIMIT 1""",
        (user_id,),
    )
    weak_row = await weak_cursor.fetchone()
    weak_subject = dict(weak_row)["subject"] if weak_row else "Mathematik"

    quest_templates = _generate_daily_quests({"weak_subject": weak_subject})

    quests = []
    for qt in quest_templates:
        await db.execute(
            """INSERT INTO daily_quests (user_id, quest_id, quest_date, title, description, xp_reward, target)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, qt["quest_id"], today, qt["title"], qt["description"], qt["xp_reward"], qt["target"]),
        )
        quests.append({**qt, "progress": 0, "completed": False})

    await db.commit()
    return {"quests": quests, "date": today}


@router.post("/progress/{quest_id}")
async def update_quest_progress(
    quest_id: str,
    progress: int = 1,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Update progress on a quest."""
    user_id = current_user["id"]
    today = date.today().isoformat()

    cursor = await db.execute(
        "SELECT * FROM daily_quests WHERE user_id = ? AND quest_id = ? AND quest_date = ?",
        (user_id, quest_id, today),
    )
    quest = await cursor.fetchone()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest nicht gefunden")

    qd = dict(quest)
    if qd["completed"]:
        return {"message": "Quest bereits abgeschlossen", "completed": True}

    new_progress = min(qd["progress"] + progress, qd["target"])
    completed = new_progress >= qd["target"]

    await db.execute(
        "UPDATE daily_quests SET progress = ?, completed = ? WHERE user_id = ? AND quest_id = ? AND quest_date = ?",
        (new_progress, 1 if completed else 0, user_id, quest_id, today),
    )
    await db.commit()

    xp_earned = 0
    if completed:
        try:
            from app.routes.gamification import add_xp
            await add_xp(user_id, qd["xp_reward"], "quest", db)
            xp_earned = qd["xp_reward"]
        except Exception:
            pass

    return {
        "quest_id": quest_id,
        "progress": new_progress,
        "target": qd["target"],
        "completed": completed,
        "xp_earned": xp_earned,
    }
