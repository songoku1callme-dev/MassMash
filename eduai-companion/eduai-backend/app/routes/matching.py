"""Lerngruppen-Matching routes.

Supreme 11.0 Phase 9: KI matches students with overlapping weak subjects.
Grade ±1 filter, match_prozent based on overlap, top 10 candidates.
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
    """Find learning partners with overlapping weak subjects (grade ±1)."""
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
    my_grade_str = dict(user_row)["school_grade"] if user_row else "10"
    try:
        my_grade_num = int(my_grade_str)
    except (ValueError, TypeError):
        my_grade_num = 10

    # Supreme 11.0: Filter by grade ±1 for better matching
    valid_grades = [str(my_grade_num - 1), str(my_grade_num), str(my_grade_num + 1)]

    # Find other users with similar weaknesses (grade ±1 filter)
    candidates = []
    cursor = await db.execute(
        """SELECT DISTINCT um.user_id, u.username, u.school_grade,
           GROUP_CONCAT(DISTINCT um.subject) as weak_subjects,
           GROUP_CONCAT(DISTINCT um.topic_name) as weak_topics
           FROM user_memories um
           JOIN users u ON u.id = um.user_id
           WHERE um.schwach = 1 AND um.user_id != ?
           AND u.school_grade IN (?, ?, ?)
           GROUP BY um.user_id
           LIMIT 50""",
        (user_id, valid_grades[0], valid_grades[1], valid_grades[2]),
    )
    rows = await cursor.fetchall()

    for row in rows:
        rd = dict(row)
        their_subjects = set((rd["weak_subjects"] or "").split(","))
        their_topics = set((rd["weak_topics"] or "").split(","))

        # Calculate match_prozent based on overlap / total weak subjects
        overlap = my_weak_subjects & their_subjects
        if not overlap:
            continue

        total_weak = len(my_weak_subjects | their_subjects)
        match_prozent = round((len(overlap) / max(total_weak, 1)) * 100, 0)

        # Bonus for same grade
        if rd["school_grade"] == my_grade_str:
            match_prozent = min(100, match_prozent + 10)

        # Bonus for topic overlap
        topic_overlap = my_weak_topics & their_topics
        if topic_overlap:
            match_prozent = min(100, match_prozent + len(topic_overlap) * 5)

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
            "match_prozent": match_prozent,
            "common_subjects": list(overlap),
            "common_topics": list(topic_overlap)[:5],
            "stats": gd,
        })

    # Sort by match_prozent descending
    candidates.sort(key=lambda x: x["match_prozent"], reverse=True)

    return {"partners": candidates[:10], "my_weak_subjects": list(my_weak_subjects)}


@router.get("/vorschlaege")
async def get_vorschlaege(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Supreme 11.0: GET /api/matching/vorschlaege — top 10 learning partner suggestions."""
    # Delegate to find_lernpartner which already implements the full logic
    return await find_lernpartner(current_user, db)
