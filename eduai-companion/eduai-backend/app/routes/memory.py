"""User Memory routes - Adaptive learning with feedback loop.

Tracks weak topics, feedback (Daumen hoch/runter), and adapts quiz difficulty.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.post("/feedback")
async def submit_feedback(
    topic_id: str,
    feedback: int,  # +1 (Daumen hoch) or -1 (Daumen runter)
    subject: str = "",
    topic_name: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit feedback on a topic (Daumen hoch/runter).

    Adjusts the user's memory for adaptive learning.
    feedback: +1 = understood well, -1 = still struggling
    """
    user_id = current_user["id"]
    feedback = max(-1, min(1, feedback))  # Clamp to -1 or +1

    # Check if memory entry exists
    cursor = await db.execute(
        "SELECT * FROM user_memories WHERE user_id = ? AND topic_id = ?",
        (user_id, topic_id),
    )
    row = await cursor.fetchone()

    if row:
        row_dict = dict(row)
        new_score = row_dict["feedback_score"] + feedback
        new_times = row_dict["times_asked"] + 1
        new_correct = row_dict["times_correct"] + (1 if feedback > 0 else 0)
        # Mark as schwach if feedback_score drops below -2
        schwach = 1 if new_score <= -2 else 0

        await db.execute(
            """UPDATE user_memories SET
                feedback_score = ?, times_asked = ?, times_correct = ?,
                schwach = ?, letzte_frage = datetime('now'), updated_at = datetime('now')
            WHERE user_id = ? AND topic_id = ?""",
            (new_score, new_times, new_correct, schwach, user_id, topic_id),
        )
    else:
        schwach = 1 if feedback < 0 else 0
        await db.execute(
            """INSERT INTO user_memories
                (user_id, topic_id, subject, topic_name, schwach, feedback_score,
                 times_asked, times_correct)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
            (user_id, topic_id, subject, topic_name, schwach, feedback,
             1 if feedback > 0 else 0),
        )

    await db.commit()

    return {
        "topic_id": topic_id,
        "feedback": feedback,
        "schwach": bool(schwach),
        "message": "Feedback gespeichert" if feedback > 0 else "Thema als schwach markiert",
    }


@router.get("/weak-topics")
async def get_weak_topics(
    subject: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get user's weak topics for adaptive learning reminders."""
    user_id = current_user["id"]

    if subject:
        cursor = await db.execute(
            """SELECT topic_id, subject, topic_name, feedback_score, times_asked,
                      times_correct, letzte_frage
            FROM user_memories WHERE user_id = ? AND subject = ? AND schwach = 1
            ORDER BY feedback_score ASC""",
            (user_id, subject),
        )
    else:
        cursor = await db.execute(
            """SELECT topic_id, subject, topic_name, feedback_score, times_asked,
                      times_correct, letzte_frage
            FROM user_memories WHERE user_id = ? AND schwach = 1
            ORDER BY feedback_score ASC""",
            (user_id,),
        )

    rows = await cursor.fetchall()
    return {
        "weak_topics": [dict(r) for r in rows],
        "count": len(rows),
    }


@router.get("/stats")
async def get_memory_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get overall memory/learning stats for the user."""
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT COUNT(*) as total FROM user_memories WHERE user_id = ?", (user_id,)
    )
    total_row = await cursor.fetchone()
    total = dict(total_row)["total"] if total_row else 0

    cursor = await db.execute(
        "SELECT COUNT(*) as weak FROM user_memories WHERE user_id = ? AND schwach = 1",
        (user_id,),
    )
    weak_row = await cursor.fetchone()
    weak = dict(weak_row)["weak"] if weak_row else 0

    cursor = await db.execute(
        """SELECT subject, COUNT(*) as count, SUM(schwach) as weak_count
        FROM user_memories WHERE user_id = ?
        GROUP BY subject""",
        (user_id,),
    )
    by_subject = [dict(r) for r in await cursor.fetchall()]

    return {
        "total_topics_tracked": total,
        "weak_topics_count": weak,
        "strong_topics_count": total - weak,
        "by_subject": by_subject,
    }


@router.get("/profile")
async def get_learning_profile(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get full User Memory 2.0 learning profile.

    Returns: schwache_themen, starke_themen, letzte_fehler, niveau_pro_fach, quiz_streak etc.
    """
    user_id = current_user["id"]

    # Weak topics
    cursor = await db.execute(
        """SELECT topic_id, subject, topic_name, feedback_score, times_asked, times_correct
        FROM user_memories WHERE user_id = ? AND schwach = 1
        ORDER BY feedback_score ASC LIMIT 20""",
        (user_id,),
    )
    weak = [dict(r) for r in await cursor.fetchall()]

    # Strong topics (feedback_score > 2)
    cursor = await db.execute(
        """SELECT topic_id, subject, topic_name, feedback_score, times_asked, times_correct
        FROM user_memories WHERE user_id = ? AND schwach = 0 AND feedback_score > 2
        ORDER BY feedback_score DESC LIMIT 20""",
        (user_id,),
    )
    strong = [dict(r) for r in await cursor.fetchall()]

    # Last errors (most recent weak entries)
    cursor = await db.execute(
        """SELECT topic_id, subject, topic_name, letzte_frage
        FROM user_memories WHERE user_id = ? AND schwach = 1
        ORDER BY letzte_frage DESC LIMIT 10""",
        (user_id,),
    )
    last_errors = [dict(r) for r in await cursor.fetchall()]

    # Niveau pro Fach
    cursor = await db.execute(
        """SELECT subject,
            COUNT(*) as total,
            SUM(CASE WHEN schwach = 1 THEN 1 ELSE 0 END) as weak_count,
            AVG(feedback_score) as avg_score
        FROM user_memories WHERE user_id = ?
        GROUP BY subject""",
        (user_id,),
    )
    niveau = []
    for r in await cursor.fetchall():
        d = dict(r)
        avg = d.get("avg_score", 0) or 0
        if avg >= 3:
            level = "fortgeschritten"
        elif avg >= 0:
            level = "mittel"
        else:
            level = "anfaenger"
        niveau.append({**d, "niveau": level})

    # Gamification stats
    gam_data = {}
    try:
        cursor = await db.execute(
            "SELECT xp, level, level_name, streak_days, quizzes_completed FROM gamification WHERE user_id = ?",
            (user_id,),
        )
        gam_row = await cursor.fetchone()
        if gam_row:
            gam_data = dict(gam_row)
    except Exception:
        pass

    return {
        "schwache_themen": weak,
        "starke_themen": strong,
        "letzte_fehler": last_errors,
        "niveau_pro_fach": niveau,
        "gamification": gam_data,
    }


@router.get("/adaptive-prompt")
async def get_adaptive_prompt(
    subject: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get an adaptive prompt hint based on user's weak topics.

    Returns a reminder string to prepend to AI system prompts.
    """
    user_id = current_user["id"]

    cursor = await db.execute(
        """SELECT topic_name, feedback_score FROM user_memories
        WHERE user_id = ? AND subject = ? AND schwach = 1
        ORDER BY feedback_score ASC LIMIT 5""",
        (user_id, subject),
    )
    rows = await cursor.fetchall()
    weak_topics = [dict(r) for r in rows]

    if not weak_topics:
        return {"prompt": "", "weak_topics": []}

    topic_names = [t["topic_name"] for t in weak_topics if t["topic_name"]]
    prompt = (
        f"ERINNERUNG: Der Sch\u00fcler hat Schwierigkeiten mit: {', '.join(topic_names)}. "
        "Erkl\u00e4re diese Themen besonders gr\u00fcndlich und gib zus\u00e4tzliche Beispiele."
    )

    return {"prompt": prompt, "weak_topics": weak_topics}
