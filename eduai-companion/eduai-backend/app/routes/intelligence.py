"""KI Intelligence routes - Lernstil, Emotionen, Feynman, Sokrates, Wissenslücken-Scanner.

Supreme 9.0 Phase 3: Makes the KI dramatically smarter.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.ki_intelligence import (
    detect_lernstil, get_lernstil_prompt,
    detect_emotion, get_emotion_prompt,
    generate_diagnostic_questions, analyze_gaps,
    build_weekly_plan_prompt, FEYNMAN_SYSTEM_PROMPT, SOKRATES_PROMPT,
)
from app.services.groq_llm import call_groq_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/lernstil")
async def get_lernstil(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Detect user's learning style from their chat history."""
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT messages FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 3",
        (user_id,),
    )
    rows = await cursor.fetchall()
    all_messages = []
    for row in rows:
        try:
            msgs = json.loads(dict(row)["messages"])
            all_messages.extend(msgs)
        except Exception:
            pass

    lernstil = await detect_lernstil(all_messages)
    return {
        "lernstil": lernstil,
        "beschreibung": {
            "visuell": "Du lernst am besten mit Bildern, Diagrammen und visuellen Darstellungen.",
            "auditiv": "Du lernst am besten durch Zuhören und ausführliche Erklärungen.",
            "kinesthetisch": "Du lernst am besten durch Ausprobieren und praktische Übungen.",
            "lesen": "Du lernst am besten durch Lesen, Stichpunkte und Zusammenfassungen.",
        }.get(lernstil, ""),
        "tipps": {
            "visuell": ["Erstelle Mind-Maps", "Nutze Karteikarten mit Farben", "Zeichne Diagramme"],
            "auditiv": ["Erkläre Themen laut", "Nutze die TTS-Funktion", "Diskutiere in Gruppen-Chats"],
            "kinesthetisch": ["Löse viele Übungsaufgaben", "Nutze den Quiz-Modus", "Experimentiere selbst"],
            "lesen": ["Schreibe Zusammenfassungen", "Nutze die Notizen-Funktion", "Erstelle Stichpunktlisten"],
        }.get(lernstil, []),
    }


@router.post("/feynman")
async def feynman_test(
    thema: str,
    erklärung: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Feynman-Technik: Student explains a topic, KI evaluates understanding."""
    response = call_groq_llm(
        prompt=f"Thema: {thema}\n\nMeine Erklärung:\n{erklärung}",
        system_prompt=FEYNMAN_SYSTEM_PROMPT,
        subject="general",
        level="intermediate",
        language="de",
        task_type="explanation",
    )

    # Award XP for using Feynman technique
    try:
        from app.routes.gamification import add_xp
        await add_xp(current_user["id"], 15, "feynman", db)
    except Exception:
        pass

    return {"bewertung": response, "thema": thema}


@router.post("/sokrates")
async def sokrates_dialog(
    frage: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Sokrates-Methode: KI asks guiding questions instead of giving direct answers."""
    response = call_groq_llm(
        prompt=frage,
        system_prompt=SOKRATES_PROMPT,
        subject="general",
        level="intermediate",
        language="de",
        task_type="explanation",
    )

    return {"antwort": response, "methode": "sokrates"}


@router.get("/wissensscan/start")
async def start_wissensscan(
    subject: str = "math",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Start a knowledge gap scan - generate diagnostic questions."""
    cursor = await db.execute(
        "SELECT school_grade FROM users WHERE id = ?", (current_user["id"],)
    )
    row = await cursor.fetchone()
    grade = dict(row).get("school_grade", "10") if row else "10"

    questions = await generate_diagnostic_questions(subject, grade)
    return {"subject": subject, "grade": grade, "questions": questions}


@router.post("/wissensscan/result")
async def wissensscan_result(
    subject: str,
    answers: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Analyze knowledge gap scan results."""
    try:
        answers_list = json.loads(answers)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid answers format")

    # Get the questions that were generated (stored temporarily)
    cursor = await db.execute(
        "SELECT school_grade FROM users WHERE id = ?", (current_user["id"],)
    )
    row = await cursor.fetchone()
    grade = dict(row).get("school_grade", "10") if row else "10"

    questions = await generate_diagnostic_questions(subject, grade)
    result = analyze_gaps(answers_list, questions)

    # Store gaps in user_memories for adaptive learning
    user_id = current_user["id"]
    for gap in result.get("gaps", []):
        topic_id = f"gap_{subject}_{gap.replace(' ', '_')}"
        try:
            await db.execute(
                """INSERT OR REPLACE INTO user_memories (user_id, topic_id, subject, topic_name, schwach, feedback_score, times_asked)
                VALUES (?, ?, ?, ?, 1, -2, 1)""",
                (user_id, topic_id, subject, gap),
            )
        except Exception:
            pass
    await db.commit()

    return {**result, "subject": subject}


@router.get("/weekly-plan")
async def get_weekly_plan(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate a personalized weekly study plan."""
    user_id = current_user["id"]

    # Get user info
    cursor = await db.execute(
        "SELECT school_grade, school_type FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    user_info = dict(row) if row else {"school_grade": "10", "school_type": "Gymnasium"}
    user_info["grade"] = user_info.get("school_grade", "10")

    # Get weak topics
    cursor = await db.execute(
        "SELECT topic_name FROM user_memories WHERE user_id = ? AND schwach = 1 ORDER BY feedback_score ASC LIMIT 5",
        (user_id,),
    )
    weak_rows = await cursor.fetchall()
    weak_topics = [dict(r)["topic_name"] for r in weak_rows if dict(r).get("topic_name")]

    # Get upcoming exams from calendar
    exams = []
    try:
        cursor = await db.execute(
            """SELECT title, exam_date, subject FROM exam_calendar
            WHERE user_id = ? AND exam_date >= date('now') ORDER BY exam_date LIMIT 5""",
            (user_id,),
        )
        exam_rows = await cursor.fetchall()
        exams = [f"{dict(r)['subject']}: {dict(r)['title']} ({dict(r)['exam_date']})" for r in exam_rows]
    except Exception:
        pass

    prompt = build_weekly_plan_prompt(user_info, weak_topics, exams)
    plan = call_groq_llm(
        prompt=prompt,
        system_prompt="Du bist ein Lerncoach. Erstelle einen konkreten, motivierenden Wochenplan.",
        subject="general",
        level="intermediate",
        language="de",
        task_type="explanation",
    )

    return {"plan": plan, "weak_topics": weak_topics, "upcoming_exams": exams}
