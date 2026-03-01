"""Lerngruppen-Matching routes.

Supreme 10.0 Phase 5: KI matches students with similar weaknesses.
"""
import json
import logging
from fastapi import APIRouter, Depends
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.get("/lernpartner")
async def find_lernpartner(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Find learning partners with similar weaknesses."""
    user_id = current_user["id"]

    # Get current user's weak topics
    cursor = await db.execute(
        """SELECT DISTINCT subject, topic_name FROM user_memories
        WHERE user_id = ? AND schwach = 1""",
        (user_id,),
    )
    my_weak = await cursor.fetchall()
    my_weak_subjects = set()
    my_weak_topics = set()
    for row in my_weak:
        rd = dict(row)
        my_weak_subjects.add(rd["subject"])
        if rd["topic_name"]:
            my_weak_topics.add(rd["topic_name"])

    if not my_weak_subjects:
        return {"partners": [], "message": "Keine Schwaechen erkannt. Mache mehr Quizze!"}

    # Get current user's grade
    cursor = await db.execute("SELECT school_grade FROM users WHERE id = ?", (user_id,))
    user_row = await cursor.fetchone()
    my_grade = dict(user_row)["school_grade"] if user_row else "10"

    # Find other users with similar weaknesses (same grade preferred)
    candidates = []
    cursor = await db.execute(
        """SELECT DISTINCT um.user_id, u.username, u.school_grade,
           GROUP_CONCAT(DISTINCT um.subject) as weak_subjects,
           GROUP_CONCAT(DISTINCT um.topic_name) as weak_topics
           FROM user_memories um
           JOIN users u ON u.id = um.user_id
           WHERE um.schwach = 1 AND um.user_id != ?
           GROUP BY um.user_id
           ORDER BY u.school_grade LIMIT 20""",
        (user_id,),
    )
    rows = await cursor.fetchall()

    for row in rows:
        rd = dict(row)
        their_subjects = set((rd["weak_subjects"] or "").split(","))
        their_topics = set((rd["weak_topics"] or "").split(","))

        # Calculate match score
        subject_overlap = len(my_weak_subjects & their_subjects)
        topic_overlap = len(my_weak_topics & their_topics) if my_weak_topics else 0

        if subject_overlap == 0:
            continue

        total = max(len(my_weak_subjects), 1)
        match_score = round((subject_overlap / total) * 100, 0)

        # Bonus for same grade
        if rd["school_grade"] == my_grade:
            match_score = min(100, match_score + 10)

        # Get their gamification stats
        g_cursor = await db.execute(
            "SELECT xp, level, level_name, streak_days FROM gamification WHERE user_id = ?",
            (rd["user_id"],),
        )
        g_row = await g_cursor.fetchone()
        gd = dict(g_row) if g_row else {"xp": 0, "level": 1, "level_name": "Neuling", "streak_days": 0}

        candidates.append({
            "user_id": rd["user_id"],
            "username": rd["username"],
            "school_grade": rd["school_grade"],
            "match_score": match_score,
            "common_subjects": list(my_weak_subjects & their_subjects),
            "common_topics": list(my_weak_topics & their_topics)[:5],
            "stats": gd,
        })

    # Sort by match score
    candidates.sort(key=lambda x: x["match_score"], reverse=True)

    return {"partners": candidates[:5], "my_weak_subjects": list(my_weak_subjects)}
