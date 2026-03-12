"""Abitur-Simulation routes - Timed exam simulation with scoring (Max only).

Features:
- Start/pause/resume/submit exam simulations
- Timer with auto-pause support
- German grading (0-15 Notenpunkte)
- Wochen-Coach: 8-week study plans generated via Groq
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.groq_llm import call_groq_llm
from app.services.ai_engine import build_system_prompt, generate_quiz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/abitur", tags=["abitur"])


def _require_max_tier(user_tier: str) -> None:
    """Raise 403 if user is not on Max tier."""
    if user_tier != "max":
        raise HTTPException(
            status_code=403,
            detail="Abitur-Simulation ist nur für Max-Abonnenten verfügbar. Upgrade auf Max für 19,99€/Monat.",
        )


def _score_to_notenpunkte(score_percent: float) -> int:
    """Convert percentage score to German Notenpunkte (0-15)."""
    if score_percent >= 95:
        return 15
    elif score_percent >= 90:
        return 14
    elif score_percent >= 85:
        return 13
    elif score_percent >= 80:
        return 12
    elif score_percent >= 75:
        return 11
    elif score_percent >= 70:
        return 10
    elif score_percent >= 65:
        return 9
    elif score_percent >= 60:
        return 8
    elif score_percent >= 55:
        return 7
    elif score_percent >= 50:
        return 6
    elif score_percent >= 45:
        return 5
    elif score_percent >= 40:
        return 4
    elif score_percent >= 33:
        return 3
    elif score_percent >= 27:
        return 2
    elif score_percent >= 20:
        return 1
    return 0


def _notenpunkte_to_note(punkte: int) -> str:
    """Convert Notenpunkte to German grade string."""
    grades = {
        15: "1+ (sehr gut)", 14: "1 (sehr gut)", 13: "1- (sehr gut)",
        12: "2+ (gut)", 11: "2 (gut)", 10: "2- (gut)",
        9: "3+ (befriedigend)", 8: "3 (befriedigend)", 7: "3- (befriedigend)",
        6: "4+ (ausreichend)", 5: "4 (ausreichend)", 4: "4- (ausreichend)",
        3: "5+ (mangelhaft)", 2: "5 (mangelhaft)", 1: "5- (mangelhaft)",
        0: "6 (ungenügend)",
    }
    return grades.get(punkte, "unbekannt")


async def _get_user_tier(user_id: int, db: aiosqlite.Connection) -> str:
    """Get user's subscription tier."""
    cursor = await db.execute(
        "SELECT subscription_tier FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return (dict(row).get("subscription_tier", "free") or "free") if row else "free"


@router.post("/start")
async def start_simulation(
    subject: str,
    duration_minutes: int = 180,
    num_questions: int = 20,
    thema_custom: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Start a new Abitur simulation exam.

    Args:
        subject: Subject for the exam (e.g. 'math', 'german')
        duration_minutes: Exam duration (180 or 240 minutes)
        num_questions: Number of questions (default 20)
        thema_custom: Optional free text topic for the exam
    """
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    # Clamp duration
    duration_minutes = max(60, min(300, duration_minutes))

    # Use custom topic if provided, otherwise default
    topic_label = thema_custom.strip() if thema_custom and thema_custom.strip() else f"Abitur {subject}"

    # If custom topic provided, try Tavily search for context
    tavily_context = ""
    if thema_custom and thema_custom.strip():
        try:
            from app.routes.research import _search_tavily
            results = await _search_tavily(f"Abitur {subject} {thema_custom} Aufgaben 2024 2025 2026", max_results=3)
            for r in results:
                tavily_context += f"\nQuelle: {r.get('title', '')}\n{r.get('content', '')}\n"
        except Exception as e:
            logger.warning("Tavily search failed for Abitur topic: %s", e)

    # Generate Abitur-level questions
    questions = generate_quiz(
        subject=subject,
        difficulty="advanced",
        num_questions=num_questions,
        quiz_type="mcq",
        language="de",
        topic=topic_label,
    )

    # Store simulation
    cursor = await db.execute(
        """INSERT INTO abitur_simulations
            (user_id, subject, duration_minutes, questions, status)
        VALUES (?, ?, ?, ?, 'active')""",
        (user_id, subject, duration_minutes, json.dumps(questions, ensure_ascii=False)),
    )
    await db.commit()
    sim_id = cursor.lastrowid

    # Return questions without correct answers
    public_questions = [
        {
            "id": q["id"],
            "question": q["question"],
            "options": q.get("options", []),
            "difficulty": q["difficulty"],
            "topic": q.get("topic", subject),
        }
        for q in questions
    ]

    return {
        "simulation_id": sim_id,
        "subject": subject,
        "duration_minutes": duration_minutes,
        "questions": public_questions,
        "status": "active",
        "start_time": datetime.now().isoformat(),
    }


@router.post("/pause")
async def pause_simulation(
    simulation_id: int,
    elapsed_seconds: int = 0,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Pause an active Abitur simulation."""
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    cursor = await db.execute(
        "SELECT * FROM abitur_simulations WHERE id = ? AND user_id = ? AND status = 'active'",
        (simulation_id, user_id),
    )
    sim = await cursor.fetchone()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation nicht gefunden oder bereits beendet")

    await db.execute(
        """UPDATE abitur_simulations SET
            status = 'paused', pause_time = datetime('now'),
            paused_elapsed_seconds = ?
        WHERE id = ?""",
        (elapsed_seconds, simulation_id),
    )
    await db.commit()

    return {"simulation_id": simulation_id, "status": "paused", "elapsed_seconds": elapsed_seconds}


@router.post("/resume")
async def resume_simulation(
    simulation_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Resume a paused Abitur simulation."""
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    cursor = await db.execute(
        "SELECT * FROM abitur_simulations WHERE id = ? AND user_id = ? AND status = 'paused'",
        (simulation_id, user_id),
    )
    sim = await cursor.fetchone()
    if not sim:
        raise HTTPException(status_code=404, detail="Keine pausierte Simulation gefunden")

    sim_dict = dict(sim)
    await db.execute(
        "UPDATE abitur_simulations SET status = 'active', pause_time = '' WHERE id = ?",
        (simulation_id,),
    )
    await db.commit()

    return {
        "simulation_id": simulation_id,
        "status": "active",
        "elapsed_seconds": sim_dict["paused_elapsed_seconds"],
        "remaining_minutes": sim_dict["duration_minutes"] - (sim_dict["paused_elapsed_seconds"] // 60),
    }


@router.post("/submit")
async def submit_simulation(
    simulation_id: int,
    answers: list[dict],
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit answers for an Abitur simulation and get scored results.

    Args:
        simulation_id: ID of the simulation
        answers: List of {question_id: int, user_answer: str}
    """
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    cursor = await db.execute(
        "SELECT * FROM abitur_simulations WHERE id = ? AND user_id = ? AND status IN ('active', 'paused')",
        (simulation_id, user_id),
    )
    sim = await cursor.fetchone()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation nicht gefunden")

    sim_dict = dict(sim)
    questions = json.loads(sim_dict["questions"])

    # Build answer map
    correct_map = {q["id"]: q["correct_answer"] for q in questions}
    total = len(correct_map)
    correct = 0

    graded = []
    for ans in answers:
        q_id = ans.get("question_id")
        user_answer = ans.get("user_answer", "").strip()
        server_answer = correct_map.get(q_id, "")
        is_correct = user_answer.lower() == server_answer.lower()
        if is_correct:
            correct += 1
        graded.append({
            "question_id": q_id,
            "user_answer": user_answer,
            "correct_answer": server_answer,
            "is_correct": is_correct,
        })

    score_percent = (correct / total * 100) if total > 0 else 0
    note_punkte = _score_to_notenpunkte(score_percent)
    note_text = _notenpunkte_to_note(note_punkte)

    # Update simulation
    await db.execute(
        """UPDATE abitur_simulations SET
            status = 'completed', score = ?, note_punkte = ?,
            answers = ?
        WHERE id = ?""",
        (score_percent, note_punkte, json.dumps(graded, ensure_ascii=False), simulation_id),
    )
    await db.commit()

    # Award gamification XP for Abitur completion
    try:
        from app.routes.gamification import add_xp
        await add_xp(user_id, 50, "abitur", db)
    except Exception:
        pass  # Non-fatal

    return {
        "simulation_id": simulation_id,
        "subject": sim_dict["subject"],
        "total_questions": total,
        "correct_answers": correct,
        "score_percent": round(score_percent, 1),
        "note_punkte": note_punkte,
        "note": note_text,
        "graded_answers": graded,
        "status": "completed",
    }


@router.get("/history")
async def simulation_history(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get Abitur simulation history for the user."""
    user_id = current_user["id"]
    cursor = await db.execute(
        """SELECT id, subject, duration_minutes, score, note_punkte, status, created_at
        FROM abitur_simulations WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 20""",
        (user_id,),
    )
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["note"] = _notenpunkte_to_note(d.get("note_punkte", 0))
        results.append(d)
    return {"simulations": results}


# === Wochen-Coach ===

@router.post("/coach/plan")
async def create_study_plan(
    subject: str,
    weeks: int = 8,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate an 8-week Abitur study plan via Groq LLM.

    Max tier only.
    """
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    weeks = max(1, min(12, weeks))

    # Get user's weak topics for this subject
    cursor = await db.execute(
        """SELECT topic_name FROM user_memories
        WHERE user_id = ? AND subject = ? AND schwach = 1
        ORDER BY feedback_score ASC LIMIT 10""",
        (user_id, subject),
    )
    weak_rows = await cursor.fetchall()
    weak_topics = [dict(r)["topic_name"] for r in weak_rows if dict(r)["topic_name"]]

    weak_hint = ""
    if weak_topics:
        weak_hint = f"\nSchwache Themen des Schülers: {', '.join(weak_topics)}. Diese besonders berücksichtigen!"

    system_prompt = (
        "Du bist ein erfahrener Abitur-Coach. Erstelle einen detaillierten Lernplan.\n"
        "Antworte NUR mit validem JSON (keine Markdown-Codeblöcke).\n"
        "Format: [{\"woche\": 1, \"thema\": \"...\", \"aufgaben\": [\"...\"], \"tage_pro_woche\": 5, \"stunden_pro_tag\": 2}]\n"
        f"Fach: {subject}. Zeitraum: {weeks} Wochen bis zum Abitur.{weak_hint}"
    )

    plan_text = call_groq_llm(
        prompt=f"Erstelle einen {weeks}-Wochen Abitur-Lernplan für {subject}.",
        system_prompt=system_prompt,
        subject=subject,
        level="advanced",
        language="de",
        is_pro=True,
    )

    # Try to parse as JSON, fallback to raw text
    try:
        plan_json = json.loads(plan_text)
    except (json.JSONDecodeError, TypeError):
        # If Groq didn't return valid JSON, wrap as structured plan
        plan_json = [
            {"woche": i + 1, "thema": f"Woche {i + 1}", "aufgaben": [plan_text], "tage_pro_woche": 5, "stunden_pro_tag": 2}
            for i in range(weeks)
        ]

    # Store plan
    cursor = await db.execute(
        """INSERT INTO wochen_coach_plans (user_id, subject, plan_json, week_count)
        VALUES (?, ?, ?, ?)""",
        (user_id, subject, json.dumps(plan_json, ensure_ascii=False), weeks),
    )
    await db.commit()
    plan_id = cursor.lastrowid

    return {
        "plan_id": plan_id,
        "subject": subject,
        "weeks": weeks,
        "plan": plan_json,
        "weak_topics_included": weak_topics,
    }


@router.get("/coach/plans")
async def get_study_plans(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get all study plans for the user."""
    user_id = current_user["id"]
    cursor = await db.execute(
        """SELECT id, subject, week_count, current_week, status, created_at
        FROM wochen_coach_plans WHERE user_id = ?
        ORDER BY created_at DESC""",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return {"plans": [dict(r) for r in rows]}


@router.get("/coach/plan/{plan_id}")
async def get_study_plan_detail(
    plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get a specific study plan with full details."""
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM wochen_coach_plans WHERE id = ? AND user_id = ?",
        (plan_id, user_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lernplan nicht gefunden")

    plan_dict = dict(row)
    plan_dict["plan"] = json.loads(plan_dict.pop("plan_json", "[]"))
    return plan_dict


@router.put("/coach/plan/{plan_id}/progress")
async def update_plan_progress(
    plan_id: int,
    current_week: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Update the current week progress of a study plan."""
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT week_count FROM wochen_coach_plans WHERE id = ? AND user_id = ?",
        (plan_id, user_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lernplan nicht gefunden")

    week_count = dict(row)["week_count"]
    current_week = max(1, min(week_count, current_week))
    status = "completed" if current_week >= week_count else "active"

    await db.execute(
        "UPDATE wochen_coach_plans SET current_week = ?, status = ?, updated_at = datetime('now') WHERE id = ?",
        (current_week, status, plan_id),
    )
    await db.commit()

    return {"plan_id": plan_id, "current_week": current_week, "status": status}
