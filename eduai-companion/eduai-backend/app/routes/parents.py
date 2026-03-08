"""Eltern-Dashboard routes.

Supreme 11.0: Parents can link to children with email verification.
"""
import json
import logging
import os
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/parents", tags=["parents"])


@router.post("/link-child")
async def link_child(
    child_email: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Request parent-child link. Sends verification email to child."""
    parent_id = current_user["id"]

    # Find child by email
    cursor = await db.execute("SELECT id, email, username FROM users WHERE email = ?", (child_email,))
    child = await cursor.fetchone()
    if not child:
        raise HTTPException(status_code=404, detail="Kein Schüler mit dieser Email gefunden")

    child_dict = dict(child)
    child_id = child_dict["id"]

    if child_id == parent_id:
        raise HTTPException(status_code=400, detail="Du kannst dich nicht mit dir selbst verknüpfen")

    # Check if already linked
    cursor = await db.execute(
        "SELECT id FROM parent_links WHERE parent_id = ? AND child_id = ?",
        (parent_id, child_id),
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Bereits verknuepft")

    # Generate verification token
    token = secrets.token_urlsafe(32)

    # Create pending link request
    await db.execute(
        "INSERT INTO parent_link_requests (parent_id, child_email, token) VALUES (?, ?, ?)",
        (parent_id, child_email, token),
    )
    await db.commit()

    # Send verification email to child via Resend
    resend_key = os.getenv("RESEND_API_KEY", "")
    frontend_url = os.getenv("FRONTEND_URL", "https://mass-mash.vercel.app")
    if resend_key:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_key}"},
                    json={
                        "from": "Lumnos <noreply@lumnos.de>",
                        "to": [child_email],
                        "subject": "Eltern-Verknüpfung bestätigen - Lumnos",
                        "html": (
                            f"<p>Hallo {child_dict['username']}!</p>"
                            f"<p>Ein Elternteil möchte sich mit deinem Lumnos-Account verknüpfen, "
                            f"um deinen Lernfortschritt zu sehen.</p>"
                            f'<p><a href="{frontend_url}/parent-verify/{token}">Verknüpfung bestätigen</a></p>'
                            f'<p>Oder: <a href="{frontend_url}/parent-reject/{token}">Ablehnen</a></p>'
                            f"<p>Dein Lumnos Team</p>"
                        ),
                    },
                )
        except Exception as e:
            logger.warning("Failed to send parent verification email: %s", e)

    return {
        "message": f"Verifizierungsmail an {child_email} gesendet! Der Schüler muss bestätigen.",
        "status": "pending",
    }


@router.get("/verify/{token}")
async def verify_parent_link(
    token: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Child confirms the parent-child link (public endpoint via email link)."""
    cursor = await db.execute(
        "SELECT * FROM parent_link_requests WHERE token = ? AND status = 'pending'",
        (token,),
    )
    req = await cursor.fetchone()
    if not req:
        raise HTTPException(status_code=404, detail="Ungueltiger oder abgelaufener Link")

    req_dict = dict(req)
    parent_id = req_dict["parent_id"]
    child_email = req_dict["child_email"]

    # Find child
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", (child_email,))
    child = await cursor.fetchone()
    if not child:
        raise HTTPException(status_code=404, detail="Schüler nicht gefunden")

    child_id = dict(child)["id"]

    # Create verified link
    await db.execute(
        "INSERT OR IGNORE INTO parent_links (parent_id, child_id, verified) VALUES (?, ?, 1)",
        (parent_id, child_id),
    )
    await db.execute(
        "UPDATE parent_link_requests SET status = 'verified' WHERE token = ?",
        (token,),
    )
    await db.commit()

    return {"message": "Eltern-Verknüpfung bestätigt! Dein Elternteil kann jetzt deinen Fortschritt sehen."}


@router.get("/reject/{token}")
async def reject_parent_link(
    token: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Child rejects the parent-child link."""
    cursor = await db.execute(
        "SELECT id FROM parent_link_requests WHERE token = ? AND status = 'pending'",
        (token,),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Ungueltiger oder abgelaufener Link")

    await db.execute(
        "UPDATE parent_link_requests SET status = 'rejected' WHERE token = ?",
        (token,),
    )
    await db.commit()

    return {"message": "Verknüpfung abgelehnt."}


@router.get("/children")
async def get_children(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get list of linked children with their stats."""
    parent_id = current_user["id"]

    cursor = await db.execute(
        """SELECT u.id, u.username, u.email, u.school_grade, u.school_type,
           pl.verified, pl.created_at as linked_at
           FROM parent_links pl
           JOIN users u ON u.id = pl.child_id
           WHERE pl.parent_id = ?""",
        (parent_id,),
    )
    children = await cursor.fetchall()

    result = []
    for child in children:
        cd = dict(child)
        child_id = cd["id"]

        # Get gamification stats
        g_cursor = await db.execute(
            "SELECT xp, level, level_name, streak_days, quizzes_completed FROM gamification WHERE user_id = ?",
            (child_id,),
        )
        g_row = await g_cursor.fetchone()
        gd = dict(g_row) if g_row else {"xp": 0, "level": 1, "level_name": "Neuling", "streak_days": 0, "quizzes_completed": 0}

        # Get this week's activity
        act_cursor = await db.execute(
            """SELECT COUNT(*) as cnt FROM activity_log
            WHERE user_id = ? AND created_at >= datetime('now', '-7 days')""",
            (child_id,),
        )
        act_row = await act_cursor.fetchone()
        week_activities = dict(act_row)["cnt"] if act_row else 0

        # Get this week's learning time (pomodoro minutes)
        pom_cursor = await db.execute(
            """SELECT COUNT(*) as cnt FROM activity_log
            WHERE user_id = ? AND activity_type = 'pomodoro'
            AND created_at >= datetime('now', '-7 days')""",
            (child_id,),
        )
        pom_row = await pom_cursor.fetchone()
        week_pomodoros = dict(pom_row)["cnt"] if pom_row else 0

        # Get recent quiz scores
        quiz_cursor = await db.execute(
            """SELECT score FROM quiz_results
            WHERE user_id = ? AND completed_at >= datetime('now', '-7 days')
            ORDER BY completed_at DESC LIMIT 10""",
            (child_id,),
        )
        quiz_rows = await quiz_cursor.fetchall()
        avg_score = 0.0
        if quiz_rows:
            scores = [dict(r)["score"] for r in quiz_rows]
            avg_score = round(sum(scores) / len(scores), 1)

        # Get upcoming exams from calendar
        exam_cursor = await db.execute(
            """SELECT description, created_at FROM activity_log
            WHERE user_id = ? AND activity_type = 'exam_created'
            ORDER BY created_at DESC LIMIT 3""",
            (child_id,),
        )
        exam_rows = await exam_cursor.fetchall()
        exams = [dict(r)["description"] for r in exam_rows]

        # Get weak subjects from user_memories
        weak_cursor = await db.execute(
            """SELECT DISTINCT subject FROM user_memories
            WHERE user_id = ? AND schwach = 1 LIMIT 5""",
            (child_id,),
        )
        weak_rows = await weak_cursor.fetchall()
        weak_subjects = [dict(r)["subject"] for r in weak_rows]

        result.append({
            "id": child_id,
            "username": cd["username"],
            "email": cd["email"],
            "school_grade": cd["school_grade"],
            "school_type": cd["school_type"],
            "verified": bool(cd["verified"]),
            "linked_at": cd["linked_at"],
            "stats": {
                "xp": gd["xp"],
                "level": gd["level"],
                "level_name": gd["level_name"],
                "streak_days": gd["streak_days"],
                "quizzes_completed": gd["quizzes_completed"],
                "week_activities": week_activities,
                "week_learning_minutes": week_pomodoros * 25,
                "avg_quiz_score": avg_score,
                "upcoming_exams": exams,
                "weak_subjects": weak_subjects,
            },
        })

    return {"children": result}


@router.delete("/unlink/{child_id}")
async def unlink_child(
    child_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Remove parent-child link."""
    parent_id = current_user["id"]
    await db.execute(
        "DELETE FROM parent_links WHERE parent_id = ? AND child_id = ?",
        (parent_id, child_id),
    )
    await db.commit()
    return {"message": "Verknüpfung entfernt"}
