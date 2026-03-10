"""Tournament routes: daily tournaments with rankings, prizes, and scheduling.

Daily at 18:00 UTC: auto-create tournament (subject rotates by weekday).
Daily at 19:00 UTC: award top 3 winners with free subscriptions.
"""
import json
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/turnier", tags=["tournaments"])

# Supreme 12.0 Phase 8: Anti-Repetition — 16 subjects rotate, no subject repeats in 16 days
ALL_TOURNAMENT_SUBJECTS = [
    "Mathematik", "Deutsch", "Physik", "Englisch", "Geschichte",
    "Biologie", "Chemie", "Informatik", "Geographie", "Kunst",
    "Musik", "Sport", "Philosophie", "Wirtschaft", "Politik", "Französisch",
]

# Themed topics per subject — ensures unique themes (no repeat in 60 days)
THEMED_TOPICS: dict[str, list[str]] = {
    "Mathematik": ["Analysis", "Stochastik", "Lineare Algebra", "Geometrie", "Trigonometrie", "Integralrechnung"],
    "Deutsch": ["Lyrik-Analyse", "Erörterung", "Expressionismus", "Faust", "Sprachwandel", "Rhetorik"],
    "Physik": ["Mechanik", "Elektrodynamik", "Quantenphysik", "Thermodynamik", "Optik", "Kernphysik"],
    "Englisch": ["Shakespeare", "American Dream", "Globalisation", "Dystopia", "Civil Rights", "Media"],
    "Geschichte": ["Weimarer Republik", "Kalter Krieg", "Industrialisierung", "Imperialismus", "NS-Zeit", "Deutsche Einheit"],
    "Biologie": ["Genetik", "Evolution", "Oekologie", "Neurobiologie", "Zellbiologie", "Immunbiologie"],
    "Chemie": ["Organische Chemie", "Elektrochemie", "Saeuren & Basen", "Redoxreaktionen", "Thermochemie", "Kunststoffe"],
    "Informatik": ["Algorithmen", "Datenstrukturen", "Netzwerke", "Kryptographie", "Datenbanken", "KI-Grundlagen"],
    "Geographie": ["Klimawandel", "Stadtentwicklung", "Plattentektonik", "Bevoelkerung", "Globalisierung", "Nachhaltigkeit"],
}

# Legacy weekday mapping as fallback
WEEKDAY_SUBJECTS = {
    0: "Mathematik",
    1: "Deutsch",
    2: "Physik",
    3: "Englisch",
    4: "Geschichte",
    5: "Biologie",
    6: "Chemie",
}

TOURNAMENT_QUESTIONS = 20
TOURNAMENT_TIME_LIMIT = 300  # 5 minutes in seconds


async def _pick_anti_repetition_subject(db: aiosqlite.Connection) -> str:
    """Pick a subject that hasn't been used in the last 16 tournament days."""
    cursor = await db.execute(
        "SELECT subject FROM tournaments ORDER BY date DESC LIMIT 16"
    )
    recent = await cursor.fetchall()
    recent_subjects = {dict(r)["subject"] for r in recent}
    available = [s for s in ALL_TOURNAMENT_SUBJECTS if s not in recent_subjects]
    if not available:
        available = ALL_TOURNAMENT_SUBJECTS
    import random
    return random.choice(available)


async def _pick_anti_repetition_theme(db: aiosqlite.Connection, subject: str) -> str:
    """Pick a theme for the subject that hasn't been used in the last 60 days."""
    themes = THEMED_TOPICS.get(subject, [subject])
    cursor = await db.execute(
        """SELECT questions FROM tournaments
        WHERE subject = ? AND date >= date('now', '-60 days')
        ORDER BY date DESC""",
        (subject,),
    )
    recent_rows = await cursor.fetchall()
    used_themes: set[str] = set()
    for r in recent_rows:
        try:
            qs = json.loads(dict(r).get("questions", "[]"))
            for q in qs:
                topic = q.get("topic", "")
                if topic:
                    used_themes.add(topic)
        except Exception:
            pass
    available = [t for t in themes if t not in used_themes]
    if not available:
        available = themes
    import random
    return random.choice(available)


async def create_daily_tournament(db: aiosqlite.Connection) -> dict:
    """Create today's tournament if it doesn't exist yet (anti-repetition)."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if today's tournament already exists
    cursor = await db.execute(
        "SELECT id, subject, status FROM tournaments WHERE date = ?", (today,)
    )
    existing = await cursor.fetchone()
    if existing:
        return dict(existing)

    # Supreme 12.0: Anti-repetition subject + theme selection
    subject = await _pick_anti_repetition_subject(db)
    theme = await _pick_anti_repetition_theme(db, subject)

    # Generate tournament questions using Groq if available
    questions = []
    try:
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {
                                "role": "system",
                                "content": "Du bist ein deutscher Lehrer. Erstelle Turnier-Quizfragen."
                            },
                            {
                                "role": "user",
                                "content": f"""Erstelle {TOURNAMENT_QUESTIONS} schwierige Multiple-Choice-Fragen für ein Turnier im Fach {subject}.
Format als JSON-Array:
[{{"id": 1, "question": "...", "options": ["A", "B", "C", "D"], "correct": "A", "topic": "..."}}]
Nur das JSON-Array, keine Erklärung."""
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4000,
                    },
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    # Extract JSON from response
                    start = content.find("[")
                    end = content.rfind("]") + 1
                    if start >= 0 and end > start:
                        questions = json.loads(content[start:end])
    except Exception as e:
        logger.warning("Failed to generate tournament questions via Groq: %s", e)

    # Fallback: generate simple questions
    if not questions:
        for i in range(1, TOURNAMENT_QUESTIONS + 1):
            questions.append({
                "id": i,
                "question": f"{subject}-Frage {i}: Was ist die richtige Antwort?",
                "options": ["A", "B", "C", "D"],
                "correct": "A",
                "topic": subject,
            })

    cursor = await db.execute(
        """INSERT INTO tournaments (subject, date, status, questions, num_questions, time_limit_seconds)
        VALUES (?, ?, 'active', ?, ?, ?)""",
        (subject, today, json.dumps(questions), TOURNAMENT_QUESTIONS, TOURNAMENT_TIME_LIMIT),
    )
    await db.commit()
    tournament_id = cursor.lastrowid

    logger.info("Created daily tournament: id=%s subject=%s date=%s", tournament_id, subject, today)
    return {"id": tournament_id, "subject": subject, "status": "active", "date": today}


async def award_tournament_winners(db: aiosqlite.Connection) -> list:
    """Award top 3 winners of today's tournament with free subscriptions."""
    today = datetime.now().strftime("%Y-%m-%d")

    cursor = await db.execute(
        "SELECT id FROM tournaments WHERE date = ? AND status = 'active'", (today,)
    )
    tournament = await cursor.fetchone()
    if not tournament:
        return []

    tournament_id = tournament[0]

    # Get top 3
    cursor = await db.execute(
        """SELECT te.user_id, te.score, te.correct_answers, te.time_taken_seconds, u.username
        FROM tournament_entries te
        JOIN users u ON te.user_id = u.id
        WHERE te.tournament_id = ?
        ORDER BY te.score DESC, te.time_taken_seconds ASC
        LIMIT 3""",
        (tournament_id,),
    )
    winners = await cursor.fetchall()

    prizes = []
    for rank, winner in enumerate(winners, 1):
        w = dict(winner)
        user_id = w["user_id"]

        if rank == 1:
            # 1st place: 1 month Max
            tier = "max"
            days = 30
            prize_desc = "1 Monat Max gratis"
        elif rank == 2:
            # 2nd place: 1 month Pro
            tier = "pro"
            days = 30
            prize_desc = "1 Monat Pro gratis"
        else:
            # 3rd place: 1 week Pro
            tier = "pro"
            days = 7
            prize_desc = "1 Woche Pro gratis"

        expires_at = (datetime.now() + timedelta(days=days)).isoformat()
        await db.execute(
            """UPDATE users SET subscription_tier = ?, is_pro = 1,
               pro_expires_at = ?, pro_since = datetime('now')
               WHERE id = ? AND (subscription_tier = 'free' OR subscription_tier = 'pro')""",
            (tier, expires_at, user_id),
        )
        prizes.append({
            "rank": rank,
            "user_id": user_id,
            "username": w["username"],
            "score": w["score"],
            "prize": prize_desc,
        })

    # Mark tournament as completed
    await db.execute(
        "UPDATE tournaments SET status = 'completed' WHERE id = ?", (tournament_id,)
    )
    await db.commit()

    return prizes


@router.get("/aktuell")
async def get_current_tournament(db: aiosqlite.Connection = Depends(get_db)):
    """Get today's active tournament."""
    today = datetime.now().strftime("%Y-%m-%d")

    cursor = await db.execute(
        "SELECT * FROM tournaments WHERE date = ? ORDER BY id DESC LIMIT 1", (today,)
    )
    row = await cursor.fetchone()

    if not row:
        # Auto-create today's tournament
        result = await create_daily_tournament(db)
        cursor = await db.execute(
            "SELECT * FROM tournaments WHERE id = ?", (result["id"],)
        )
        row = await cursor.fetchone()

    if not row:
        return {"tournament": None, "message": "Kein Turnier heute"}

    t = dict(row)
    questions = json.loads(t.get("questions", "[]"))
    # Don't send correct answers to client
    safe_questions = []
    for q in questions:
        safe_questions.append({
            "id": q.get("id"),
            "question": q.get("question"),
            "options": q.get("options", []),
            "topic": q.get("topic", ""),
        })

    # Get participant count
    cursor = await db.execute(
        "SELECT COUNT(*) FROM tournament_entries WHERE tournament_id = ?", (t["id"],)
    )
    count_row = await cursor.fetchone()

    return {
        "tournament": {
            "id": t["id"],
            "subject": t["subject"],
            "date": t["date"],
            "status": t["status"],
            "num_questions": t["num_questions"],
            "time_limit_seconds": t["time_limit_seconds"],
            "questions": safe_questions if t["status"] == "active" else [],
            "participant_count": count_row[0] if count_row else 0,
        }
    }


@router.post("/teilnehmen")
async def join_tournament(
    tournament_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Join a tournament."""
    user_id = current_user["id"]

    # Check tournament exists and is active
    cursor = await db.execute(
        "SELECT id, status FROM tournaments WHERE id = ?", (tournament_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Turnier nicht gefunden")
    if dict(row)["status"] != "active":
        raise HTTPException(status_code=400, detail="Turnier ist nicht mehr aktiv")

    # Check if already joined
    cursor = await db.execute(
        "SELECT id FROM tournament_entries WHERE tournament_id = ? AND user_id = ?",
        (tournament_id, user_id),
    )
    if await cursor.fetchone():
        return {"message": "Du nimmst bereits teil", "tournament_id": tournament_id}

    await db.execute(
        "INSERT INTO tournament_entries (tournament_id, user_id) VALUES (?, ?)",
        (tournament_id, user_id),
    )
    await db.commit()

    return {"message": "Erfolgreich angemeldet!", "tournament_id": tournament_id}


@router.post("/abgeben")
async def submit_tournament(
    tournament_id: int,
    answers: list[dict],
    time_taken_seconds: int = 0,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit tournament answers."""
    user_id = current_user["id"]

    # Get tournament
    cursor = await db.execute(
        "SELECT * FROM tournaments WHERE id = ?", (tournament_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Turnier nicht gefunden")

    tournament = dict(row)
    questions = json.loads(tournament.get("questions", "[]"))

    # Score answers
    correct_count = 0
    for answer in answers:
        q_id = answer.get("question_id")
        user_answer = answer.get("answer", "")
        for q in questions:
            if q.get("id") == q_id and q.get("correct", "").strip().upper() == user_answer.strip().upper():
                correct_count += 1
                break

    score = int((correct_count / max(len(questions), 1)) * 1000)

    # Update or insert entry
    cursor = await db.execute(
        "SELECT id FROM tournament_entries WHERE tournament_id = ? AND user_id = ?",
        (tournament_id, user_id),
    )
    existing = await cursor.fetchone()

    if existing:
        await db.execute(
            """UPDATE tournament_entries SET score = ?, correct_answers = ?,
               time_taken_seconds = ?, answers = ?, submitted_at = datetime('now')
               WHERE tournament_id = ? AND user_id = ?""",
            (score, correct_count, time_taken_seconds, json.dumps(answers), tournament_id, user_id),
        )
    else:
        await db.execute(
            """INSERT INTO tournament_entries
               (tournament_id, user_id, score, correct_answers, time_taken_seconds, answers, submitted_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
            (tournament_id, user_id, score, correct_count, time_taken_seconds, json.dumps(answers)),
        )
    await db.commit()

    return {
        "score": score,
        "correct_answers": correct_count,
        "total_questions": len(questions),
        "time_taken_seconds": time_taken_seconds,
    }


@router.get("/rangliste")
async def get_rankings(
    tournament_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get tournament rankings."""
    cursor = await db.execute(
        """SELECT te.user_id, te.score, te.correct_answers, te.time_taken_seconds,
                  u.username, u.full_name
        FROM tournament_entries te
        JOIN users u ON te.user_id = u.id
        WHERE te.tournament_id = ? AND te.submitted_at != ''
        ORDER BY te.score DESC, te.time_taken_seconds ASC""",
        (tournament_id,),
    )
    rows = await cursor.fetchall()

    rankings = []
    for rank, row in enumerate(rows, 1):
        r = dict(row)
        rankings.append({
            "rank": rank,
            "username": r["full_name"] or r["username"],
            "score": r["score"],
            "correct_answers": r["correct_answers"],
            "time_taken_seconds": r["time_taken_seconds"],
        })

    return {"rankings": rankings, "tournament_id": tournament_id}


@router.get("/gewinner")
async def get_today_winners(db: aiosqlite.Connection = Depends(get_db)):
    """Get today's tournament winners (or latest completed tournament)."""
    cursor = await db.execute(
        """SELECT t.id, t.subject, t.date, t.status
        FROM tournaments t
        WHERE t.status = 'completed'
        ORDER BY t.date DESC LIMIT 1"""
    )
    tournament = await cursor.fetchone()
    if not tournament:
        return {"winners": [], "tournament": None}

    t = dict(tournament)
    cursor = await db.execute(
        """SELECT te.user_id, te.score, te.correct_answers, u.username, u.full_name
        FROM tournament_entries te
        JOIN users u ON te.user_id = u.id
        WHERE te.tournament_id = ? AND te.submitted_at != ''
        ORDER BY te.score DESC, te.time_taken_seconds ASC
        LIMIT 3""",
        (t["id"],),
    )
    rows = await cursor.fetchall()

    winners = []
    prizes = ["1 Monat Max gratis", "1 Monat Pro gratis", "1 Woche Pro gratis"]
    for rank, row in enumerate(rows):
        r = dict(row)
        winners.append({
            "rank": rank + 1,
            "username": r["full_name"] or r["username"],
            "score": r["score"],
            "correct_answers": r["correct_answers"],
            "prize": prizes[rank] if rank < len(prizes) else "",
        })

    return {
        "winners": winners,
        "tournament": {"id": t["id"], "subject": t["subject"], "date": t["date"]},
    }


@router.get("/verlauf")
async def get_tournament_history(db: aiosqlite.Connection = Depends(get_db)):
    """Get past tournaments."""
    cursor = await db.execute(
        """SELECT t.id, t.subject, t.date, t.status, t.num_questions,
                  (SELECT COUNT(*) FROM tournament_entries WHERE tournament_id = t.id) as participants
        FROM tournaments t
        ORDER BY t.date DESC LIMIT 30"""
    )
    rows = await cursor.fetchall()
    return {"tournaments": [dict(r) for r in rows]}
