"""Gamification routes - XP, Streaks, Levels, Achievements, Leaderboard.

Features:
- XP: Quiz +10, Chat +5, Abitur +50
- Streak: Daily login tracking
- Levels: 6 tiers (Neuling → Meister)
- Achievements: 4 types (first_quiz, streak_7, xp_1000, abitur_first)
- Leaderboard: Top 10 weekly (anonymous)
"""
import json
import logging
from datetime import datetime, date
from fastapi import APIRouter, Depends
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gamification", tags=["gamification"])

# Level thresholds — Fix 4: Rebalanciert damit Progression sich verdient anfühlt
LEVELS = [
    {"level": 1, "name": "Neuling", "min_xp": 0, "emoji": "🌱"},
    {"level": 2, "name": "Lernender", "min_xp": 100, "emoji": "📚"},
    {"level": 3, "name": "Fortgeschritten", "min_xp": 300, "emoji": "⭐"},
    {"level": 4, "name": "Experte", "min_xp": 600, "emoji": "🏆"},
    {"level": 5, "name": "Profi", "min_xp": 1000, "emoji": "💎"},
    {"level": 6, "name": "Meister", "min_xp": 3000, "emoji": "👑"},
    {"level": 7, "name": "Großmeister", "min_xp": 10000, "emoji": "🌟"},
    {"level": 8, "name": "Legende", "min_xp": 50000, "emoji": "🔥"},
    {"level": 9, "name": "Unsterblich", "min_xp": 200000, "emoji": "♾️"},
]

# Achievement definitions
ACHIEVEMENTS = [
    {"id": "first_quiz", "name": "Erster Quiz", "desc": "Dein erstes Quiz abgeschlossen!", "emoji": "🎯", "xp_reward": 25},
    {"id": "streak_7", "name": "7-Tage-Streak", "desc": "7 Tage am Stück gelernt!", "emoji": "🔥", "xp_reward": 50},
    {"id": "xp_1000", "name": "1000 XP", "desc": "1000 XP gesammelt!", "emoji": "⭐", "xp_reward": 100},
    {"id": "abitur_first", "name": "Erste Abitur-Sim", "desc": "Erste Abitur-Simulation bestanden!", "emoji": "🎓", "xp_reward": 75},
    {"id": "quiz_10", "name": "Quiz-Marathon", "desc": "10 Quizzes abgeschlossen!", "emoji": "📝", "xp_reward": 50},
    {"id": "streak_30", "name": "30-Tage-Streak", "desc": "30 Tage am Stück gelernt!", "emoji": "💪", "xp_reward": 200},
    {"id": "chat_50", "name": "Wissbegierig", "desc": "50 Chat-Nachrichten gesendet!", "emoji": "💬", "xp_reward": 50},
    {"id": "level_5", "name": "Profi-Status", "desc": "Level 5 (Profi) erreicht!", "emoji": "💎", "xp_reward": 150},
]


def _calculate_level(xp: int) -> dict:
    """Calculate level based on XP."""
    current_level = LEVELS[0]
    for lvl in LEVELS:
        if xp >= lvl["min_xp"]:
            current_level = lvl
    return current_level


async def _ensure_gamification_row(user_id: int, db: aiosqlite.Connection) -> dict:
    """Get or create gamification row for user."""
    cursor = await db.execute(
        "SELECT * FROM gamification WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)

    # Create new row
    await db.execute(
        "INSERT INTO gamification (user_id) VALUES (?)", (user_id,)
    )
    await db.commit()
    cursor = await db.execute(
        "SELECT * FROM gamification WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else {"user_id": user_id, "xp": 0, "level": 1, "level_name": "Neuling", "streak_days": 0, "achievements": "[]"}


async def add_xp(user_id: int, xp_amount: int, activity: str, db: aiosqlite.Connection) -> dict:
    """Add XP to user and check for level-ups and achievements."""
    gam = await _ensure_gamification_row(user_id, db)
    new_xp = gam["xp"] + xp_amount

    # Update streak
    today_str = date.today().isoformat()
    streak = gam["streak_days"]
    last_date = gam.get("streak_last_date", "")
    if last_date != today_str:
        if last_date == (date.today().replace(day=date.today().day)).isoformat():
            pass  # Already counted today
        else:
            # Check if yesterday
            from datetime import timedelta
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            if last_date == yesterday:
                streak += 1
            elif last_date:
                streak = 1  # Reset streak
            else:
                streak = 1  # First day

    # Calculate new level
    level_info = _calculate_level(new_xp)

    # Update counters
    quizzes = gam["quizzes_completed"] + (1 if activity == "quiz" else 0)
    chats = gam["chats_sent"] + (1 if activity == "chat" else 0)
    abitur = gam["abitur_completed"] + (1 if activity == "abitur" else 0)

    # Check achievements
    existing_achievements = json.loads(gam.get("achievements", "[]"))
    existing_ids = {a["id"] for a in existing_achievements} if isinstance(existing_achievements, list) and existing_achievements and isinstance(existing_achievements[0], dict) else set(existing_achievements)
    new_achievements = []

    achievement_checks = [
        ("first_quiz", quizzes >= 1),
        ("quiz_10", quizzes >= 10),
        ("streak_7", streak >= 7),
        ("streak_30", streak >= 30),
        ("xp_1000", new_xp >= 1000),
        ("abitur_first", abitur >= 1),
        ("chat_50", chats >= 50),
        ("level_5", level_info["level"] >= 5),
    ]

    for ach_id, condition in achievement_checks:
        if condition and ach_id not in existing_ids:
            ach_def = next((a for a in ACHIEVEMENTS if a["id"] == ach_id), None)
            if ach_def:
                new_achievements.append({"id": ach_id, "earned_at": today_str})
                new_xp += ach_def["xp_reward"]

    # Recalculate level after achievement bonus XP
    level_info = _calculate_level(new_xp)

    all_achievements = existing_achievements + new_achievements

    await db.execute(
        """UPDATE gamification SET
            xp = ?, level = ?, level_name = ?,
            streak_days = ?, streak_last_date = ?,
            quizzes_completed = ?, chats_sent = ?, abitur_completed = ?,
            achievements = ?, updated_at = datetime('now')
        WHERE user_id = ?""",
        (new_xp, level_info["level"], level_info["name"],
         streak, today_str, quizzes, chats, abitur,
         json.dumps(all_achievements, ensure_ascii=False), user_id),
    )
    await db.commit()

    return {
        "xp_gained": xp_amount,
        "total_xp": new_xp,
        "level": level_info["level"],
        "level_name": level_info["name"],
        "level_emoji": level_info["emoji"],
        "streak_days": streak,
        "new_achievements": new_achievements,
    }


@router.get("/profile")
async def get_gamification_profile(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get user's gamification profile (XP, Level, Streak, Achievements)."""
    user_id = current_user["id"]
    gam = await _ensure_gamification_row(user_id, db)

    level_info = _calculate_level(gam["xp"])
    # Find next level
    next_level = None
    for lvl in LEVELS:
        if lvl["min_xp"] > gam["xp"]:
            next_level = lvl
            break

    achievements = json.loads(gam.get("achievements", "[]"))

    return {
        "xp": gam["xp"],
        "level": level_info["level"],
        "level_name": level_info["name"],
        "level_emoji": level_info["emoji"],
        "xp_to_next_level": next_level["min_xp"] - gam["xp"] if next_level else 0,
        "next_level_name": next_level["name"] if next_level else "Max",
        "streak_days": gam["streak_days"],
        "quizzes_completed": gam["quizzes_completed"],
        "chats_sent": gam["chats_sent"],
        "abitur_completed": gam["abitur_completed"],
        "achievements": achievements,
        "all_achievements": ACHIEVEMENTS,
        "all_levels": LEVELS,
    }


@router.get("/leaderboard")
async def get_leaderboard(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get weekly anonymous leaderboard (Top 10)."""
    cursor = await db.execute(
        """SELECT g.user_id, g.xp, g.level, g.level_name, g.streak_days,
                  u.username
        FROM gamification g
        JOIN users u ON g.user_id = u.id
        ORDER BY g.xp DESC LIMIT 10"""
    )
    rows = await cursor.fetchall()

    leaderboard = []
    for i, r in enumerate(rows):
        d = dict(r)
        # Anonymize: show first 2 chars + ***
        username = d.get("username", "Anonym")
        anon_name = username[:2] + "***" if len(username) > 2 else username
        leaderboard.append({
            "rank": i + 1,
            "name": anon_name,
            "xp": d["xp"],
            "level": d["level"],
            "level_name": d["level_name"],
            "streak_days": d["streak_days"],
            "is_you": d["user_id"] == current_user["id"],
        })

    return {"leaderboard": leaderboard}


@router.post("/add-xp")
async def add_xp_endpoint(
    xp: int = 10,
    activity: str = "quiz",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Add XP to user (called internally after quiz/chat/abitur)."""
    result = await add_xp(current_user["id"], xp, activity, db)
    return result
