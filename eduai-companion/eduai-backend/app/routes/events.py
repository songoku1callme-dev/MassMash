"""Saisonale Events routes.

Supreme 10.0 Phase 7: Seasonal events and challenges.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

# Pre-defined seasonal events — always at least 2-3 active
SEASONAL_EVENTS = [
    {
        "id": "abitur_sprint_2026",
        "name": "Abitur-Sprint 2026",
        "description": "30 Tage intensiv lernen! Doppelte XP für alle Abitur-relevanten Fächer.",
        "event_type": "abitur",
        "start_date": "2026-01-01",
        "end_date": "2026-06-30",
        "rewards": {"badge": "abi_ready", "xp_bonus": 500},
        "challenges": [
            {"title": "50 Abitur-Quizze", "target": 50, "xp": 200},
            {"title": "Alle Fächer mindestens 1x", "target": 16, "xp": 300},
            {"title": "5 Abitur-Simulationen", "target": 5, "xp": 500},
        ],
    },
    {
        "id": "fruehlings_challenge_2026",
        "name": "Frühjahrs-Challenge",
        "description": "Jeden Tag eine neue Quest! Sammle Bonus-XP den ganzen Frühling.",
        "event_type": "fruehling",
        "start_date": "2026-03-01",
        "end_date": "2026-04-30",
        "rewards": {"badge": "spring_learner", "xp_bonus": 300},
        "challenges": [
            {"title": "30 Tage Streak", "target": 30, "xp": 500},
            {"title": "100 Quiz-Fragen beantworten", "target": 100, "xp": 200},
            {"title": "5 verschiedene Fächer üben", "target": 5, "xp": 150},
        ],
    },
    {
        "id": "wochenend_turnier_2026",
        "name": "Wochenend-Turnier",
        "description": "Samstag + Sonntag Bonus-XP! Tritt gegen andere Schüler an.",
        "event_type": "turnier",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "rewards": {"badge": "weekend_warrior", "xp_bonus": 150},
        "challenges": [
            {"title": "An 10 Turnieren teilnehmen", "target": 10, "xp": 300},
            {"title": "3 Turniere gewinnen", "target": 3, "xp": 500},
        ],
    },
    {
        "id": "neues_schuljahr_2026",
        "name": "Neues Schuljahr 2026",
        "description": "Neues Jahr, neue Noten! Setze Ziele und starte durch.",
        "event_type": "schulstart",
        "start_date": "2026-08-15",
        "end_date": "2026-09-30",
        "rewards": {"badge": "fresh_start", "xp_bonus": 200},
        "challenges": [
            {"title": "Profil aktualisieren", "target": 1, "xp": 50},
            {"title": "10 Quizze in der ersten Woche", "target": 10, "xp": 150},
            {"title": "Lernplan erstellen", "target": 1, "xp": 100},
        ],
    },
    {
        "id": "winter_challenge_2026",
        "name": "Winter-Lern-Challenge 2026",
        "description": "24 Tage Adventskalender: Jeden Tag eine Aufgabe lösen!",
        "event_type": "advent",
        "start_date": "2026-12-01",
        "end_date": "2026-12-24",
        "rewards": {"badge": "winter_learner", "xp_bonus": 300},
        "challenges": [
            {"title": "24 Tage am Stück lernen", "target": 24, "xp": 500},
            {"title": "12 verschiedene Fächer", "target": 12, "xp": 200},
        ],
    },
]


@router.get("/active")
async def get_active_events(
    current_user: dict = Depends(get_current_user),
):
    """Get currently active seasonal events."""
    now = datetime.now().strftime("%Y-%m-%d")

    active = []
    for event in SEASONAL_EVENTS:
        if event["start_date"] <= now <= event["end_date"]:
            days_left = (datetime.strptime(event["end_date"], "%Y-%m-%d") - datetime.now()).days
            active.append({
                **event,
                "days_left": max(0, days_left),
                "is_active": True,
            })

    return {"events": active, "total": len(active)}


@router.get("/all")
async def get_all_events(
    current_user: dict = Depends(get_current_user),
):
    """Get all seasonal events (past, active, future)."""
    now = datetime.now().strftime("%Y-%m-%d")

    events = []
    for event in SEASONAL_EVENTS:
        status = "active" if event["start_date"] <= now <= event["end_date"] else (
            "upcoming" if now < event["start_date"] else "ended"
        )
        events.append({**event, "status": status})

    return {"events": events}


@router.get("/progress/{event_id}")
async def get_event_progress(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get user's progress in a seasonal event."""
    user_id = current_user["id"]

    event = next((e for e in SEASONAL_EVENTS if e["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event nicht gefunden")

    # Calculate progress based on activity within event period
    challenges_progress = []
    for challenge in event["challenges"]:
        # Count relevant activities in the event period
        if "Quiz" in challenge["title"] or "Quizze" in challenge["title"]:
            cursor = await db.execute(
                """SELECT COUNT(*) as cnt FROM quiz_results
                WHERE user_id = ? AND completed_at BETWEEN ? AND ?""",
                (user_id, event["start_date"], event["end_date"]),
            )
        elif "Simulation" in challenge["title"]:
            cursor = await db.execute(
                """SELECT COUNT(*) as cnt FROM abitur_simulations
                WHERE user_id = ? AND status = 'completed'
                AND created_at BETWEEN ? AND ?""",
                (user_id, event["start_date"], event["end_date"]),
            )
        elif "Fächer" in challenge["title"] or "Fächer" in challenge["title"]:
            cursor = await db.execute(
                """SELECT COUNT(DISTINCT subject) as cnt FROM quiz_results
                WHERE user_id = ? AND completed_at BETWEEN ? AND ?""",
                (user_id, event["start_date"], event["end_date"]),
            )
        elif "Tage" in challenge["title"]:
            cursor = await db.execute(
                """SELECT COUNT(DISTINCT date(created_at)) as cnt FROM activity_log
                WHERE user_id = ? AND created_at BETWEEN ? AND ?""",
                (user_id, event["start_date"], event["end_date"]),
            )
        else:
            cursor = await db.execute(
                """SELECT COUNT(*) as cnt FROM activity_log
                WHERE user_id = ? AND created_at BETWEEN ? AND ?""",
                (user_id, event["start_date"], event["end_date"]),
            )

        row = await cursor.fetchone()
        current = dict(row)["cnt"] if row else 0

        challenges_progress.append({
            "title": challenge["title"],
            "target": challenge["target"],
            "progress": min(current, challenge["target"]),
            "completed": current >= challenge["target"],
            "xp": challenge["xp"],
        })

    total_completed = sum(1 for c in challenges_progress if c["completed"])
    total_challenges = len(challenges_progress)

    return {
        "event_id": event_id,
        "event_name": event["name"],
        "challenges": challenges_progress,
        "total_completed": total_completed,
        "total_challenges": total_challenges,
        "all_completed": total_completed == total_challenges,
    }
