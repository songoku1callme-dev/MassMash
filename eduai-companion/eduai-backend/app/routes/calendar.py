"""Prüfungs-Kalender: Exams eintragen, KI erstellt Lernplan."""
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class ExamCreate(BaseModel):
    title: str
    subject: str
    exam_date: str  # ISO date
    topics: str = ""
    notes: str = ""


class ExamUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    exam_date: str | None = None
    topics: str | None = None
    notes: str | None = None


async def _ensure_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            topics TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            study_plan TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    await db.commit()


@router.get("/exams")
async def list_exams(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all upcoming exams."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "SELECT * FROM exams WHERE user_id = ? ORDER BY exam_date ASC",
        (current_user["id"],),
    )
    exams = [dict(r) for r in await cursor.fetchall()]
    return {"exams": exams}


@router.post("/exams")
async def create_exam(
    exam: ExamCreate,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new exam entry."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "INSERT INTO exams (user_id, title, subject, exam_date, topics, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (current_user["id"], exam.title, exam.subject, exam.exam_date, exam.topics, exam.notes),
    )
    await db.commit()
    return {"id": cursor.lastrowid, "title": exam.title}


@router.delete("/exams/{exam_id}")
async def delete_exam(
    exam_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Delete an exam."""
    await _ensure_tables(db)
    await db.execute(
        "DELETE FROM exams WHERE id = ? AND user_id = ?",
        (exam_id, current_user["id"]),
    )
    await db.commit()
    return {"status": "deleted"}


@router.post("/exams/{exam_id}/study-plan")
async def generate_study_plan(
    exam_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate an AI study plan working backwards from the exam date."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "SELECT * FROM exams WHERE id = ? AND user_id = ?",
        (exam_id, current_user["id"]),
    )
    exam = await cursor.fetchone()
    if not exam:
        raise HTTPException(status_code=404, detail="Klausur nicht gefunden")

    exam_dict = dict(exam)
    try:
        exam_date = datetime.fromisoformat(exam_dict["exam_date"])
    except ValueError:
        exam_date = datetime.now() + timedelta(days=14)

    days_until = max(1, (exam_date - datetime.now()).days)

    from app.routes.chat import call_groq_llm

    prompt = f"""Erstelle einen Lernplan für eine Klausur.

Klausur: {exam_dict['title']}
Fach: {exam_dict['subject']}
Datum: {exam_dict['exam_date']} (in {days_until} Tagen)
Themen: {exam_dict['topics'] or 'Nicht angegeben'}

Erstelle einen Tag-für-Tag Lernplan rückwärts vom Klausurdatum.
Format: JSON-Array mit [{{"tag": 1, "datum": "...", "aufgabe": "...", "dauer_minuten": 30}}]
Plane maximal {min(days_until, 14)} Tage.
Letzter Tag = Wiederholung, vorletzter = Zusammenfassung, davor = Themen einzeln."""

    try:
        response = call_groq_llm(
            prompt=prompt,
            system_prompt="Du bist ein Experte für Prüfungsvorbereitung. Antworte NUR mit validem JSON.",
            subject=exam_dict["subject"],
            level="intermediate",
            language="de",
            is_pro=True,
            temperature_override=0.3,
        )

        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        start = text.find("[")
        end = text.rfind("]")
        plan = json.loads(text[start:end + 1]) if start != -1 and end != -1 else []
    except Exception:
        plan = [
            {"tag": i + 1, "datum": (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d"),
             "aufgabe": f"Thema {i+1} lernen", "dauer_minuten": 30}
            for i in range(min(days_until, 7))
        ]

    await db.execute(
        "UPDATE exams SET study_plan = ? WHERE id = ?",
        (json.dumps(plan, ensure_ascii=False), exam_id),
    )
    await db.commit()

    return {"exam_id": exam_id, "study_plan": plan, "days_until_exam": days_until}
