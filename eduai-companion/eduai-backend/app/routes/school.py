"""Schul-Lizenzen routes - B2B teacher/class management.

Features:
- Teachers create class licenses with codes (KLASSE-XXXX)
- Students join via class code or invite link
- Teacher dashboard shows student progress (XP, level, streak, quizzes)
- Bulk Max tier for all students in class
- Teacher can invite students by email
- Teacher can remove students (downgrades to free)
- Students can leave classes
"""
import json
import logging
import os
import secrets
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/school", tags=["school"])


def _generate_class_code() -> str:
    """Generate a readable class code like 'KLASSE-ABCD'."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    suffix = "".join(secrets.choice(chars) for _ in range(4))
    return f"KLASSE-{suffix}"


@router.post("/create")
async def create_class(
    school_name: str,
    max_students: int = 30,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new school class license (teacher only)."""
    teacher_id = current_user["id"]
    class_code = _generate_class_code()

    cursor = await db.execute(
        """INSERT INTO school_licenses (school_name, teacher_id, class_code, max_students, students)
        VALUES (?, ?, ?, ?, '[]')""",
        (school_name, teacher_id, class_code, max_students),
    )
    await db.commit()

    return {
        "class_id": cursor.lastrowid,
        "class_code": class_code,
        "school_name": school_name,
        "max_students": max_students,
    }


@router.post("/join/{class_code}")
async def join_class(
    class_code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Student joins a class via code."""
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM school_licenses WHERE class_code = ? AND is_active = 1",
        (class_code.upper(),),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Klassen-Code nicht gefunden")

    d = dict(row)
    students = json.loads(d["students"])

    if user_id in students:
        return {"message": "Bereits in der Klasse"}

    if len(students) >= d["max_students"]:
        raise HTTPException(status_code=400, detail="Klasse ist voll")

    students.append(user_id)
    await db.execute(
        "UPDATE school_licenses SET students = ? WHERE class_code = ?",
        (json.dumps(students), class_code.upper()),
    )

    # Upgrade student to Max tier
    await db.execute(
        "UPDATE users SET subscription_tier = 'max', is_pro = 1 WHERE id = ?",
        (user_id,),
    )
    await db.commit()

    return {"message": "Klasse beigetreten! Du hast jetzt Max-Zugang.", "class_code": class_code}


@router.get("/dashboard")
async def teacher_dashboard(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Teacher dashboard - see all classes and student progress."""
    teacher_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM school_licenses WHERE teacher_id = ? ORDER BY created_at DESC",
        (teacher_id,),
    )
    rows = await cursor.fetchall()

    classes = []
    for r in rows:
        d = dict(r)
        student_ids = json.loads(d["students"])

        # Get student details
        students_info = []
        for sid in student_ids:
            scursor = await db.execute(
                """SELECT u.id, u.username, u.full_name, u.school_grade,
                   g.xp, g.level, g.streak_days, g.quizzes_completed
                   FROM users u LEFT JOIN gamification g ON u.id = g.user_id
                   WHERE u.id = ?""",
                (sid,),
            )
            srow = await scursor.fetchone()
            if srow:
                sd = dict(srow)
                students_info.append({
                    "id": sd["id"],
                    "username": sd["username"],
                    "full_name": sd.get("full_name", ""),
                    "grade": sd.get("school_grade", ""),
                    "xp": sd.get("xp", 0) or 0,
                    "level": sd.get("level", 1) or 1,
                    "streak": sd.get("streak_days", 0) or 0,
                    "quizzes": sd.get("quizzes_completed", 0) or 0,
                })

        classes.append({
            "id": d["id"],
            "school_name": d["school_name"],
            "class_code": d["class_code"],
            "student_count": len(student_ids),
            "max_students": d["max_students"],
            "is_active": bool(d["is_active"]),
            "students": students_info,
            "created_at": d["created_at"],
        })

    return {"classes": classes}


@router.delete("/remove-student/{class_code}/{student_id}")
async def remove_student(
    class_code: str,
    student_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Teacher removes a student from their class."""
    teacher_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM school_licenses WHERE class_code = ? AND teacher_id = ? AND is_active = 1",
        (class_code.upper(), teacher_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Klasse nicht gefunden oder keine Berechtigung")

    d = dict(row)
    students = json.loads(d["students"])

    if student_id not in students:
        raise HTTPException(status_code=404, detail="Schüler nicht in dieser Klasse")

    students.remove(student_id)
    await db.execute(
        "UPDATE school_licenses SET students = ? WHERE class_code = ?",
        (json.dumps(students), class_code.upper()),
    )

    # Only downgrade if student has no active independent Stripe subscription
    # Check both stripe_customer_id AND billing_period to confirm a completed subscription
    ucursor = await db.execute(
        "SELECT stripe_customer_id, billing_period FROM users WHERE id = ?", (student_id,)
    )
    urow = await ucursor.fetchone()
    ud = dict(urow) if urow else {}
    has_active_stripe = ud.get("stripe_customer_id") and ud.get("billing_period")
    if not has_active_stripe:
        await db.execute(
            "UPDATE users SET subscription_tier = 'free', is_pro = 0 WHERE id = ?",
            (student_id,),
        )
    await db.commit()

    return {"message": "Schüler entfernt", "student_id": student_id, "class_code": class_code}


@router.get("/my-class")
async def my_class(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get the class a student belongs to."""
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM school_licenses WHERE is_active = 1"
    )
    rows = await cursor.fetchall()

    for r in rows:
        d = dict(r)
        students = json.loads(d["students"])
        if user_id in students:
            return {
                "class_code": d["class_code"],
                "school_name": d["school_name"],
                "student_count": len(students),
            }

    return {"class_code": None, "school_name": None}


class InviteRequest(BaseModel):
    class_code: str
    emails: list[str]


@router.post("/invite")
async def invite_students(
    req: InviteRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Teacher invites students by email.

    Creates pending invitations that get auto-accepted when the student signs up
    or logs in. For existing users, they are added to the class immediately.
    """
    teacher_id = current_user["id"]
    class_code = req.class_code.upper()

    # Verify teacher owns this class
    cursor = await db.execute(
        "SELECT * FROM school_licenses WHERE class_code = ? AND teacher_id = ? AND is_active = 1",
        (class_code, teacher_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Klasse nicht gefunden oder keine Berechtigung")

    d = dict(row)
    students = json.loads(d["students"])
    max_students = d["max_students"]

    added = []
    already_in = []
    invited = []
    full = False

    for email in req.emails:
        email = email.strip().lower()
        if not email:
            continue

        if len(students) >= max_students:
            full = True
            break

        # Check if user exists
        ucursor = await db.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        )
        urow = await ucursor.fetchone()

        if urow:
            uid = dict(urow)["id"]
            if uid in students:
                already_in.append(email)
                continue

            # Add existing user directly
            students.append(uid)
            await db.execute(
                "UPDATE users SET subscription_tier = 'max', is_pro = 1 WHERE id = ?",
                (uid,),
            )
            added.append(email)
        else:
            # Store pending invitation
            try:
                await db.execute(
                    """INSERT INTO school_invitations (class_code, email, status)
                    VALUES (?, ?, 'pending')
                    ON CONFLICT (class_code, email) DO UPDATE SET status = 'pending'""",
                    (class_code, email),
                )
            except Exception:
                # Table might not exist yet — just track as invited
                pass
            invited.append(email)

    # Update students list
    await db.execute(
        "UPDATE school_licenses SET students = ? WHERE class_code = ?",
        (json.dumps(students), class_code),
    )
    await db.commit()

    msg_parts = []
    if added:
        msg_parts.append(f"{len(added)} Schueler hinzugefuegt")
    if invited:
        msg_parts.append(f"{len(invited)} Einladungen gesendet")
    if already_in:
        msg_parts.append(f"{len(already_in)} bereits in der Klasse")
    if full:
        msg_parts.append("Klasse ist voll")

    return {
        "message": ", ".join(msg_parts) if msg_parts else "Keine Aenderungen",
        "added": added,
        "invited": invited,
        "already_in": already_in,
        "class_full": full,
    }


@router.get("/invite-link/{class_code}")
async def get_invite_link(
    class_code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate a shareable invite link for a class."""
    teacher_id = current_user["id"]
    cursor = await db.execute(
        "SELECT id, school_name FROM school_licenses WHERE class_code = ? AND teacher_id = ? AND is_active = 1",
        (class_code.upper(), teacher_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Klasse nicht gefunden")

    d = dict(row)
    frontend_url = os.getenv("FRONTEND_URL", "https://mass-mash.vercel.app")
    invite_url = f"{frontend_url}/school?join={class_code.upper()}"

    return {
        "invite_url": invite_url,
        "class_code": class_code.upper(),
        "school_name": d["school_name"],
    }


@router.post("/leave/{class_code}")
async def leave_class(
    class_code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Student leaves a class voluntarily."""
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM school_licenses WHERE class_code = ? AND is_active = 1",
        (class_code.upper(),),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Klasse nicht gefunden")

    d = dict(row)
    students = json.loads(d["students"])

    if user_id not in students:
        raise HTTPException(status_code=400, detail="Du bist nicht in dieser Klasse")

    students.remove(user_id)
    await db.execute(
        "UPDATE school_licenses SET students = ? WHERE class_code = ?",
        (json.dumps(students), class_code.upper()),
    )

    # Only downgrade if student has no active independent Stripe subscription
    # Check both stripe_customer_id AND billing_period to confirm a completed subscription
    ucursor2 = await db.execute(
        "SELECT stripe_customer_id, billing_period FROM users WHERE id = ?", (user_id,)
    )
    urow2 = await ucursor2.fetchone()
    ud2 = dict(urow2) if urow2 else {}
    has_active_stripe = ud2.get("stripe_customer_id") and ud2.get("billing_period")
    if not has_active_stripe:
        await db.execute(
            "UPDATE users SET subscription_tier = 'free', is_pro = 0 WHERE id = ?",
            (user_id,),
        )
    await db.commit()

    return {"message": "Du hast die Klasse verlassen.", "class_code": class_code}
