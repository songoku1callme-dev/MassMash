"""Learning routes - profiles, progress, and learning paths."""
import json
from fastapi import APIRouter, Depends
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.schemas import (
    LearningProfileResponse, ProgressResponse, LearningPathResponse, SubjectInfo
)
from app.services.ai_engine import SUBJECTS, get_learning_path

router = APIRouter(prefix="/api", tags=["learning"])


@router.get("/subjects", response_model=list[SubjectInfo])
async def list_subjects():
    """List all available subjects."""
    return [
        SubjectInfo(
            id=s["id"],
            name=s["name"],
            name_de=s["name_de"],
            icon=s["icon"],
            description=s["description"],
            description_de=s["description_de"],
            topics=s["topics"]
        )
        for s in SUBJECTS.values()
    ]


@router.get("/profile", response_model=list[LearningProfileResponse])
async def get_profiles(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Get learning profiles for all subjects."""
    cursor = await db.execute(
        "SELECT * FROM learning_profiles WHERE user_id = ?",
        (current_user["id"],)
    )
    profiles = await cursor.fetchall()

    return [
        LearningProfileResponse(
            subject=dict(p)["subject"],
            proficiency_level=dict(p)["proficiency_level"],
            mastery_score=round(dict(p)["mastery_score"] * 100, 1),
            topics_completed=dict(p)["topics_completed"],
            total_questions_answered=dict(p)["total_questions_answered"],
            correct_answers=dict(p)["correct_answers"],
            accuracy=round(dict(p)["correct_answers"] / dict(p)["total_questions_answered"] * 100, 1) if dict(p)["total_questions_answered"] > 0 else 0,
            last_active=dict(p)["last_active"]
        )
        for p in profiles
    ]


@router.get("/progress", response_model=ProgressResponse)
async def get_progress(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Get overall learning progress."""
    user_id = current_user["id"]

    # Get profiles
    cursor = await db.execute(
        "SELECT * FROM learning_profiles WHERE user_id = ?", (user_id,)
    )
    profiles = await cursor.fetchall()

    profile_list = [
        LearningProfileResponse(
            subject=dict(p)["subject"],
            proficiency_level=dict(p)["proficiency_level"],
            mastery_score=round(dict(p)["mastery_score"] * 100, 1),
            topics_completed=dict(p)["topics_completed"],
            total_questions_answered=dict(p)["total_questions_answered"],
            correct_answers=dict(p)["correct_answers"],
            accuracy=round(dict(p)["correct_answers"] / dict(p)["total_questions_answered"] * 100, 1) if dict(p)["total_questions_answered"] > 0 else 0,
            last_active=dict(p)["last_active"]
        )
        for p in profiles
    ]

    # Count sessions
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM chat_sessions WHERE user_id = ?", (user_id,)
    )
    sessions = (await cursor.fetchone())[0]

    # Count quizzes
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM quiz_results WHERE user_id = ?", (user_id,)
    )
    quizzes = (await cursor.fetchone())[0]

    # Recent activity
    cursor = await db.execute(
        """SELECT activity_type, subject, description, created_at
        FROM activity_log WHERE user_id = ? ORDER BY created_at DESC LIMIT 10""",
        (user_id,)
    )
    activities = await cursor.fetchall()
    recent = [dict(a) for a in activities]

    # Calculate streak (simplified)
    cursor = await db.execute(
        """SELECT DISTINCT date(created_at) as day
        FROM activity_log WHERE user_id = ? ORDER BY day DESC LIMIT 30""",
        (user_id,)
    )
    days = [dict(d)["day"] for d in await cursor.fetchall()]
    streak = len(days) if days else 0

    return ProgressResponse(
        profiles=profile_list,
        total_sessions=sessions,
        total_quizzes=quizzes,
        recent_activity=recent,
        streak_days=streak
    )


@router.get("/learning-path/{subject}", response_model=LearningPathResponse)
async def get_learning_path_endpoint(
    subject: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Get recommended learning path for a subject."""
    user_id = current_user["id"]
    language = current_user.get("preferred_language", "de")

    # Get proficiency
    cursor = await db.execute(
        "SELECT proficiency_level FROM learning_profiles WHERE user_id = ? AND subject = ?",
        (user_id, subject)
    )
    profile = await cursor.fetchone()
    level = dict(profile)["proficiency_level"] if profile else "beginner"

    path = get_learning_path(subject, level, language)

    return LearningPathResponse(
        subject=subject,
        current_level=level,
        recommended_topics=path["topics"],
        next_milestone=path["next_milestone"]
    )
