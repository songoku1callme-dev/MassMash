"""Schul-Lizenzen routes - B2B teacher/class management.

Features:
- Teachers create class licenses with codes
- Students join via class code
- Teacher dashboard shows student progress
- Bulk Max tier for all students in class
"""
import json
import logging
import secrets
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

    # Downgrade student back to free tier
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
