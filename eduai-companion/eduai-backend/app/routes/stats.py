"""Schueler-Analyse Dashboard routes.

Supreme 12.0 Phase 10: /meine-stats page with learning analytics.
"""
import json
import logging
import os
from datetime import datetime
from fastapi import APIRouter, Depends
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
async def get_stats_overview(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get comprehensive learning statistics for the dashboard."""
    user_id = current_user["id"]

    # Total learning time (from activity log)
    cursor = await db.execute(
        "SELECT COUNT(*) as activities FROM activity_log WHERE user_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    total_activities = dict(row)["activities"] if row else 0
    # Estimate ~3 min per activity
    total_minutes = total_activities * 3

    # Quiz success rate
    cursor = await db.execute(
        """SELECT COUNT(*) as total,
           SUM(CASE WHEN score >= 70 THEN 1 ELSE 0 END) as passed
        FROM quiz_results WHERE user_id = ?""",
        (user_id,),
    )
    row = await cursor.fetchone()
    rd = dict(row) if row else {}
    total_quizzes = rd.get("total", 0) or 0
    passed_quizzes = rd.get("passed", 0) or 0
    quiz_success_rate = round(passed_quizzes / total_quizzes * 100) if total_quizzes > 0 else 0

    # Longest streak
    cursor = await db.execute(
        "SELECT streak_days, longest_streak FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    rd = dict(row) if row else {}
    current_streak = rd.get("streak_days", 0) or 0
    longest_streak = rd.get("longest_streak", current_streak) or current_streak

    # XP / IQ
    cursor = await db.execute(
        "SELECT total_xp, level FROM gamification WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    rd = dict(row) if row else {}
    total_xp = rd.get("total_xp", 0) or 0
    level = rd.get("level", 1) or 1

    # IQ score
    cursor = await db.execute(
        "SELECT score FROM iq_results WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    row = await cursor.fetchone()
    iq_score = dict(row)["score"] if row else None

    return {
        "total_learning_minutes": total_minutes,
        "total_quizzes": total_quizzes,
        "quiz_success_rate": quiz_success_rate,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_xp": total_xp,
        "level": level,
        "iq_score": iq_score,
    }


@router.get("/per-subject")
async def get_stats_per_subject(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get quiz performance broken down by subject."""
    user_id = current_user["id"]

    cursor = await db.execute(
        """SELECT subject,
           COUNT(*) as total,
           ROUND(AVG(score), 1) as avg_score,
           MAX(score) as best_score
        FROM quiz_results WHERE user_id = ?
        GROUP BY subject ORDER BY avg_score DESC""",
        (user_id,),
    )
    rows = await cursor.fetchall()

    subjects = []
    for r in rows:
        rd = dict(r)
        subjects.append({
            "subject": rd["subject"],
            "total_quizzes": rd["total"],
            "avg_score": rd.get("avg_score", 0) or 0,
            "best_score": rd.get("best_score", 0) or 0,
        })

    # Identify strongest and weakest
    strongest = subjects[:3] if subjects else []
    weakest = list(reversed(subjects[-3:])) if len(subjects) >= 3 else []

    return {
        "subjects": subjects,
        "strongest": strongest,
        "weakest": weakest,
    }


@router.get("/weekly")
async def get_weekly_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get learning activity per week (last 12 weeks)."""
    user_id = current_user["id"]

    cursor = await db.execute(
        """SELECT strftime('%Y-W%W', created_at) as week,
           COUNT(*) as activities,
           activity_type
        FROM activity_log WHERE user_id = ?
        AND created_at >= date('now', '-84 days')
        GROUP BY week, activity_type
        ORDER BY week""",
        (user_id,),
    )
    rows = await cursor.fetchall()

    weekly: dict[str, dict] = {}
    for r in rows:
        rd = dict(r)
        w = rd["week"]
        if w not in weekly:
            weekly[w] = {"week": w, "total": 0, "chat": 0, "quiz": 0, "other": 0}
        weekly[w]["total"] += rd["activities"]
        atype = rd.get("activity_type", "other")
        if atype in ("chat", "quiz"):
            weekly[w][atype] += rd["activities"]
        else:
            weekly[w]["other"] += rd["activities"]

    return {"weeks": list(weekly.values())}


@router.get("/xp-history")
async def get_xp_history(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get XP earned over time (daily for last 30 days)."""
    user_id = current_user["id"]

    cursor = await db.execute(
        """SELECT DATE(created_at) as day, SUM(xp_earned) as xp
        FROM xp_log WHERE user_id = ?
        AND created_at >= date('now', '-30 days')
        GROUP BY day ORDER BY day""",
        (user_id,),
    )
    rows = await cursor.fetchall()

    history = []
    for r in rows:
        rd = dict(r)
        history.append({"date": rd["day"], "xp": rd.get("xp", 0) or 0})

    return {"history": history}


@router.post("/ki-analyse")
async def ki_analyse(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """KI-powered analysis of all user stats (Supreme 12.0 Phase 10)."""
    user_id = current_user["id"]

    # Gather stats
    overview = await get_stats_overview(current_user, db)
    per_subject = await get_stats_per_subject(current_user, db)

    # Build analysis prompt
    stats_summary = json.dumps({
        "overview": overview,
        "subjects": per_subject.get("subjects", [])[:10],
        "strongest": per_subject.get("strongest", []),
        "weakest": per_subject.get("weakest", []),
    }, ensure_ascii=False)

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return {
            "analysis": (
                f"Basierend auf deinen Daten: Du hast {overview['total_quizzes']} Quizze gemacht "
                f"mit einer Erfolgsrate von {overview['quiz_success_rate']}%. "
                f"Dein Streak ist {overview['current_streak']} Tage. Weiter so!"
            ),
            "generated_by": "template",
        }

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein Lern-Analytiker. Analysiere die Statistiken eines Schuelers "
                        "und gib einen personalisierten Bericht mit konkreten Tipps. "
                        "Antworte auf Deutsch, maximal 300 Woerter. "
                        "Strukturiere: 1) Zusammenfassung 2) Staerken 3) Schwaechen 4) Konkrete Tipps"
                    ),
                },
                {"role": "user", "content": f"Analysiere meine Lernstatistiken:\n{stats_summary}"},
            ],
            max_tokens=600,
            temperature=0.7,
        )
        analysis = resp.choices[0].message.content or "Analyse konnte nicht erstellt werden."
    except Exception as e:
        logger.error("KI-Analyse failed: %s", e)
        analysis = (
            f"Deine Statistiken: {overview['total_quizzes']} Quizze, "
            f"{overview['quiz_success_rate']}% Erfolgsrate, {overview['current_streak']} Tage Streak. "
            "Tipp: Fokussiere dich auf deine schwachen Faecher!"
        )

    return {"analysis": analysis, "generated_by": "groq"}
