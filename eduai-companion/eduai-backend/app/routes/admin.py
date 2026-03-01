"""Admin routes: stats dashboard, monitoring config, and API key testing."""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import aiosqlite
from app.core.database import get_db
from app.core.config import settings
from app.core.monitoring import get_monitoring_frontend_config

logger = logging.getLogger(__name__)

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


class TestKeyRequest(BaseModel):
    """Request body for API key testing."""
    key_type: str  # "groq", "clerk", "posthog", "sentry"
    api_key: str = ""


@router.post("/test-key")
async def test_api_key(request: TestKeyRequest):
    """Test if an API key is valid by making a minimal API call.

    Supports: groq, clerk, posthog, sentry.
    Does NOT store the key — frontend handles storage/display.
    """
    key_type = request.key_type.lower()

    if key_type == "groq":
        # Test Groq key by making a tiny completion request
        test_key = request.api_key or settings.GROQ_API_KEY
        if not test_key:
            return {"valid": False, "message": "Kein Groq API Key konfiguriert.", "key_type": "groq"}
        try:
            from groq import Groq
            client = Groq(api_key=test_key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "Sage nur: OK"}],
                max_tokens=5,
            )
            response_text = completion.choices[0].message.content or ""
            return {
                "valid": True,
                "message": f"Groq API funktioniert! Antwort: {response_text.strip()}",
                "key_type": "groq",
                "model": "llama-3.1-8b-instant",
            }
        except Exception as exc:
            logger.warning("Groq key test failed: %s", exc)
            return {"valid": False, "message": f"Groq API Fehler: {exc}", "key_type": "groq"}

    elif key_type == "server-status":
        # Return current server configuration status
        return {
            "valid": True,
            "key_type": "server-status",
            "groq_configured": bool(settings.GROQ_API_KEY),
            "message": "Server-Status abgerufen.",
        }

    else:
        return {"valid": False, "message": f"Unbekannter Key-Typ: {key_type}", "key_type": key_type}
