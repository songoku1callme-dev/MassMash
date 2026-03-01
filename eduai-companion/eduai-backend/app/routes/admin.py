"""Admin routes: stats dashboard and monitoring config."""

from fastapi import APIRouter, Depends
import aiosqlite
from app.core.database import get_db
from app.core.monitoring import get_monitoring_frontend_config

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    """Return platform statistics for the admin dashboard.

    No auth required for now — in production this should be restricted
    to admin users via a role check or API key.
    """
    stats: dict = {}

    # Total users
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    row = await cursor.fetchone()
    stats["total_users"] = row[0] if row else 0

    # Total chat sessions
    cursor = await db.execute("SELECT COUNT(*) FROM chat_sessions")
    row = await cursor.fetchone()
    stats["total_chat_sessions"] = row[0] if row else 0

    # Total quizzes completed
    cursor = await db.execute("SELECT COUNT(*) FROM quiz_results")
    row = await cursor.fetchone()
    stats["total_quizzes"] = row[0] if row else 0

    # Average quiz score
    cursor = await db.execute("SELECT AVG(score) FROM quiz_results")
    row = await cursor.fetchone()
    stats["avg_quiz_score"] = round(row[0], 1) if row and row[0] is not None else 0.0

    # Proficiency distribution
    cursor = await db.execute(
        "SELECT proficiency_level, COUNT(*) FROM learning_profiles GROUP BY proficiency_level"
    )
    rows = await cursor.fetchall()
    stats["proficiency_distribution"] = {row[0]: row[1] for row in rows}

    # Subject popularity (by chat sessions)
    cursor = await db.execute(
        "SELECT subject, COUNT(*) as cnt FROM chat_sessions GROUP BY subject ORDER BY cnt DESC"
    )
    rows = await cursor.fetchall()
    stats["subject_popularity"] = {row[0]: row[1] for row in rows}

    # Recent activity count (last 24h)
    cursor = await db.execute(
        "SELECT COUNT(*) FROM activity_log WHERE created_at > datetime('now', '-1 day')"
    )
    row = await cursor.fetchone()
    stats["activity_last_24h"] = row[0] if row else 0

    return stats


@router.get("/monitoring-config")
async def monitoring_config():
    """Return monitoring configuration for the frontend (safe to expose).

    Returns whether Sentry/PostHog are enabled and their public keys.
    """
    return get_monitoring_frontend_config()
