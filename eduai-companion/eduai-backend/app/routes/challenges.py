"""Klassen-Challenges routes - Soziales Lernen.

Supreme 9.0 Phase 11: Teachers create challenges, students compete.
"""
import json
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


@router.post("/create")
async def create_challenge(
    title: str,
    description: str,
    subject: str = "math",
    target_score: int = 80,
    deadline_days: int = 7,
    xp_reward: int = 100,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new class challenge (teacher or any user)."""
    user_id = current_user["id"]
    challenge_id = str(uuid.uuid4())[:8]

    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, subject, description, metadata)
        VALUES (?, 'challenge_created', ?, ?, ?)""",
        (user_id, subject, f"Challenge: {title}",
         json.dumps({
             "challenge_id": challenge_id,
             "title": title,
             "description": description,
             "subject": subject,
             "target_score": target_score,
             "deadline_days": deadline_days,
             "xp_reward": xp_reward,
             "creator_id": user_id,
             "participants": [],
             "completed_by": [],
         })),
    )
    await db.commit()

    return {
        "challenge_id": challenge_id,
        "title": title,
        "description": description,
        "subject": subject,
        "target_score": target_score,
        "deadline_days": deadline_days,
        "xp_reward": xp_reward,
    }


@router.get("/list")
async def list_challenges(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all active challenges."""
    cursor = await db.execute(
        """SELECT user_id, description, metadata, created_at FROM activity_log
        WHERE activity_type = 'challenge_created'
        AND created_at >= datetime('now', '-30 days')
        ORDER BY created_at DESC LIMIT 20""",
    )
    rows = await cursor.fetchall()

    challenges = []
    for row in rows:
        r = dict(row)
        try:
            meta = json.loads(r["metadata"])
            # Count participants
            participant_cursor = await db.execute(
                """SELECT COUNT(*) as cnt FROM activity_log
                WHERE activity_type = 'challenge_join' AND description LIKE ?""",
                (f"%{meta['challenge_id']}%",),
            )
            p_row = await participant_cursor.fetchone()
            participant_count = dict(p_row)["cnt"] if p_row else 0

            # Count completions
            complete_cursor = await db.execute(
                """SELECT COUNT(*) as cnt FROM activity_log
                WHERE activity_type = 'challenge_complete' AND description LIKE ?""",
                (f"%{meta['challenge_id']}%",),
            )
            c_row = await complete_cursor.fetchone()
            complete_count = dict(c_row)["cnt"] if c_row else 0

            challenges.append({
                "challenge_id": meta["challenge_id"],
                "title": meta["title"],
                "description": meta.get("description", ""),
                "subject": meta.get("subject", ""),
                "target_score": meta.get("target_score", 80),
                "xp_reward": meta.get("xp_reward", 100),
                "deadline_days": meta.get("deadline_days", 7),
                "creator_id": meta.get("creator_id", r["user_id"]),
                "created_at": r["created_at"],
                "participants": participant_count,
                "completions": complete_count,
            })
        except Exception:
            pass

    return {"challenges": challenges}


@router.post("/join/{challenge_id}")
async def join_challenge(
    challenge_id: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Join a challenge."""
    user_id = current_user["id"]

    # Check if already joined
    cursor = await db.execute(
        """SELECT id FROM activity_log
        WHERE user_id = ? AND activity_type = 'challenge_join' AND description LIKE ?""",
        (user_id, f"%{challenge_id}%"),
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Du nimmst bereits an dieser Challenge teil")

    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, subject, description, metadata)
        VALUES (?, 'challenge_join', 'challenge', ?, ?)""",
        (user_id, f"Challenge beigetreten: {challenge_id}",
         json.dumps({"challenge_id": challenge_id})),
    )
    await db.commit()

    return {"message": "Challenge beigetreten!", "challenge_id": challenge_id}


@router.post("/complete/{challenge_id}")
async def complete_challenge(
    challenge_id: str,
    score: int = 0,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Mark a challenge as completed by the current user."""
    user_id = current_user["id"]

    # Check if already completed
    cursor = await db.execute(
        """SELECT id FROM activity_log
        WHERE user_id = ? AND activity_type = 'challenge_complete' AND description LIKE ?""",
        (user_id, f"%{challenge_id}%"),
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Challenge bereits abgeschlossen")

    # Find challenge details
    cursor = await db.execute(
        """SELECT metadata FROM activity_log
        WHERE activity_type = 'challenge_created' AND metadata LIKE ?""",
        (f"%{challenge_id}%",),
    )
    row = await cursor.fetchone()
    xp_reward = 100
    if row:
        try:
            meta = json.loads(dict(row)["metadata"])
            xp_reward = meta.get("xp_reward", 100)
        except Exception:
            pass

    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, subject, description, metadata)
        VALUES (?, 'challenge_complete', 'challenge', ?, ?)""",
        (user_id, f"Challenge abgeschlossen: {challenge_id}",
         json.dumps({"challenge_id": challenge_id, "score": score})),
    )
    await db.commit()

    # Award XP
    try:
        from app.routes.gamification import add_xp
        await add_xp(user_id, xp_reward, "challenge", db)
    except Exception:
        pass

    return {"message": "Challenge abgeschlossen!", "xp_earned": xp_reward}
