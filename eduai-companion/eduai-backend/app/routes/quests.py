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


import random
import hashlib

# Supreme 12.0 Phase 9: 4 quest types with seed-based personalization
_ALL_SUBJECTS = [
    "Mathematik", "Deutsch", "Physik", "Englisch", "Geschichte",
    "Biologie", "Chemie", "Informatik", "Geographie", "Kunst",
    "Musik", "Philosophie", "Wirtschaft", "Politik", "Franzoesisch", "Sport",
]

_SOCIAL_QUESTS = [
    ("Duell gewinnen", "Gewinne ein Multiplayer-Quiz gegen einen anderen Schueler"),
    ("Lernpartner finden", "Finde einen Lernpartner ueber die Matching-Seite"),
    ("Gruppen-Chat", "Schreibe eine Nachricht in einem Gruppen-Chat"),
    ("Turnier-Teilnahme", "Nimm am taeglichen Turnier teil"),
    ("Hilf einem Mitschueler", "Beantworte eine Frage in der Community"),
]


def _generate_daily_quests(user_id: int, user_stats: dict) -> list[dict]:
    """Generate 4 daily quests — deterministic per user per day (seed-based)."""
    today = date.today().isoformat()

    # Seed = hash(user_id + today) → deterministic but different per user/day
    seed_str = f"{user_id}_{today}"
    seed_val = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**31)
    rng = random.Random(seed_val)

    quests = []

    # Quest 1: Practice weakest subject (personalized)
    weak = user_stats.get("weak_subject", "Mathematik")
    quests.append({
        "quest_id": f"weak_{today}",
        "title": f"Schwaeche ueben: {weak}",
        "description": f"Mache ein Quiz ueber {weak} um deine Schwaeche zu verbessern",
        "xp_reward": 50,
        "target": 1,
        "icon": "target",
        "type": "quiz",
    })

    # Quest 2: Subject not used today (seed-based variety)
    used = user_stats.get("today_subjects", [])
    unused = [s for s in _ALL_SUBJECTS if s not in used and s != weak]
    if not unused:
        unused = _ALL_SUBJECTS
    pick = rng.choice(unused)
    quests.append({
        "quest_id": f"explore_{today}",
        "title": f"Neues Fach: {pick}",
        "description": f"Lerne heute etwas in {pick} — erweitere deinen Horizont!",
        "xp_reward": 40,
        "target": 1,
        "icon": "compass",
        "type": "explore",
    })

    # Quest 3: Streak (always, but with personal context)
    streak = user_stats.get("current_streak", 0)
    streak_desc = (
        f"Halte deinen {streak}-Tage Streak am Leben!" if streak > 0
        else "Starte heute einen neuen Streak!"
    )
    quests.append({
        "quest_id": f"streak_{today}",
        "title": "Streak halten",
        "description": streak_desc,
        "xp_reward": 30,
        "target": 1,
        "icon": "flame",
        "type": "time",
    })

    # Quest 4: Social quest (seed-based variety)
    social = rng.choice(_SOCIAL_QUESTS)
    quests.append({
        "quest_id": f"social_{today}",
        "title": social[0],
        "description": social[1],
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

    # Get today's used subjects and streak for seed-based quest generation
    today_subj_cursor = await db.execute(
        """SELECT DISTINCT subject FROM activity_log
        WHERE user_id = ? AND DATE(created_at) = ?""",
        (user_id, today),
    )
    today_subjects = [dict(r)["subject"] for r in await today_subj_cursor.fetchall()]

    streak_cursor = await db.execute(
        "SELECT streak_days FROM users WHERE id = ?", (user_id,)
    )
    streak_row = await streak_cursor.fetchone()
    current_streak = dict(streak_row).get("streak_days", 0) if streak_row else 0

    quest_templates = _generate_daily_quests(user_id, {
        "weak_subject": weak_subject,
        "today_subjects": today_subjects,
        "current_streak": current_streak,
    })

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
