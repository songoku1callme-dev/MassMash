"""Adaptive Schwierigkeit routes - Auto-adjust quiz difficulty based on performance.

Phase 7: Quiz difficulty auto-adjusts based on success_rate:
- >85% correct -> schwer (hard)
- >65% correct -> mittel (medium)
- <65% correct -> leicht (easy)
"""
import logging
from fastapi import APIRouter, Depends
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/adaptive", tags=["adaptive"])


async def get_adaptive_difficulty(user_id: int, subject: str, db: aiosqlite.Connection) -> dict:
    """Calculate adaptive difficulty for a user in a given subject.

    Returns difficulty level and stats.
    """
    cursor = await db.execute(
        """SELECT COUNT(*) as total, SUM(correct_answers) as correct, SUM(total_questions) as questions
        FROM quiz_results WHERE user_id = ? AND subject = ?""",
        (user_id, subject),
    )
    row = await cursor.fetchone()
    d = dict(row) if row else {}

    total_quizzes = d.get("total", 0) or 0
    correct = d.get("correct", 0) or 0
    questions = d.get("questions", 0) or 0

    if questions == 0:
        return {"difficulty": "mittel", "success_rate": 0, "total_quizzes": 0, "recommendation": "Starte mit mittlerer Schwierigkeit"}

    success_rate = round(correct / questions * 100, 1)

    if success_rate > 85:
        difficulty = "schwer"
        recommendation = "Du bist sehr gut! Die Fragen werden schwieriger."
    elif success_rate > 65:
        difficulty = "mittel"
        recommendation = "Gutes Niveau! Weiter so."
    else:
        difficulty = "leicht"
        recommendation = "Wir passen die Schwierigkeit an, damit du besser lernst."

    return {
        "difficulty": difficulty,
        "success_rate": success_rate,
        "total_quizzes": total_quizzes,
        "correct_answers": correct,
        "total_questions": questions,
        "recommendation": recommendation,
    }


@router.get("/difficulty")
async def get_difficulty(
    subject: str = "general",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get adaptive difficulty recommendation for a subject."""
    return await get_adaptive_difficulty(current_user["id"], subject, db)


@router.get("/profile")
async def adaptive_profile(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get adaptive difficulty profile across all subjects."""
    user_id = current_user["id"]
    subjects = ["math", "german", "english", "physics", "chemistry", "biology", "history", "geography", "economics"]

    profiles = []
    for subj in subjects:
        data = await get_adaptive_difficulty(user_id, subj, db)
        if data["total_quizzes"] > 0:
            profiles.append({"subject": subj, **data})

    return {"profiles": profiles, "user_id": user_id}
