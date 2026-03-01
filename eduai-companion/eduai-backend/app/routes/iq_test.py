"""IQ-Test routes - scientifically-inspired intelligence assessment.

5 categories: Logik, Verbal, Mathe, Raum, Gedächtnis
40 questions (8 per category), 45 minutes total.
IQ calculation based on normal distribution (µ=100, σ=15).
Results saved to DB. Users can retake after 30 days.
"""
import json
import logging
import math
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.groq_llm import call_groq_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iq", tags=["iq-test"])


class IQTestAnswer(BaseModel):
    question_id: int
    answer: int  # 0-3 index of chosen option
    time_seconds: float  # time taken for this question


class IQTestSubmission(BaseModel):
    test_id: int
    answers: list[IQTestAnswer]


# Normal distribution CDF approximation (no scipy needed)
def _norm_cdf(x: float) -> float:
    """Approximate standard normal CDF using Abramowitz and Stegun formula."""
    if x < -8:
        return 0.0
    if x > 8:
        return 1.0
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x_abs = abs(x)
    t = 1.0 / (1.0 + p * x_abs)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x_abs * x_abs / 2.0)
    return 0.5 * (1.0 + sign * y)


def _norm_ppf(percentile: float) -> float:
    """Approximate inverse normal CDF (percent point function).

    Uses rational approximation (Beasley-Springer-Moro algorithm).
    """
    if percentile <= 0.0:
        return -4.0
    if percentile >= 1.0:
        return 4.0

    # Rational approximation
    p = percentile - 0.5
    if abs(p) <= 0.425:
        r = 0.180625 - p * p
        return p * (
            ((((((2.5090809287301226727e3 * r + 3.3430575583588128105e4) * r
                 + 6.7265770927008700853e4) * r + 4.5921953931549871457e4) * r
               + 1.3731693765509461125e4) * r + 1.9715909503065514427e3) * r
             + 1.3314166764078226174e2) * r + 3.3871328727963666080e0
        ) / (
            ((((((5.2264952788528545610e3 * r + 2.8729085735721942674e4) * r
                 + 3.9307895800092710610e4) * r + 2.1213794301586595867e4) * r
               + 5.3941960214247511077e3) * r + 6.8718700749205790830e2) * r
             + 4.2313330701600911252e1) * r + 1.0
        )
    else:
        r = p if p > 0 else -p
        r = math.sqrt(-2.0 * math.log(1.0 - r if p > 0 else 0.5 + p))
        val = (
            ((((((7.7454501427834140764e-4 * r + 2.2723844989269184187e-2) * r
                 + 7.2235882439343341018e-1) * r + 1.0) * r
               + 0.0) * r + 0.0) * r + 0.0)
        )
        # Simplified: use iterative Newton's method
        # Start with a rough approximation
        z = r - (2.515517 + 0.802853 * r + 0.010328 * r * r) / (
            1.0 + 1.432788 * r + 0.189269 * r * r + 0.001308 * r * r * r
        )
        return z if p > 0 else -z


def _get_iq_classification(iq: int) -> str:
    """Get IQ classification in German."""
    if iq >= 130:
        return "Hochbegabt (Top 2%)"
    if iq >= 120:
        return "Sehr intelligent (Top 10%)"
    if iq >= 110:
        return "Überdurchschnittlich (Top 25%)"
    if iq >= 90:
        return "Durchschnittlich (Mitte 50%)"
    if iq >= 80:
        return "Unterdurchschnittlich"
    return "Deutlich unterdurchschnittlich"


def _calculate_iq(answers: list[dict], questions: list[dict]) -> dict:
    """Calculate IQ score from answers using normal distribution.

    Scoring: correct answers + time bonus. Normalized to IQ scale (µ=100, σ=15).
    """
    raw_score = 0.0
    max_possible = 0.0
    kategorie_scores: dict[str, dict] = {
        "logik": {"correct": 0, "total": 0, "score": 0.0},
        "verbal": {"correct": 0, "total": 0, "score": 0.0},
        "mathe": {"correct": 0, "total": 0, "score": 0.0},
        "raum": {"correct": 0, "total": 0, "score": 0.0},
        "gedaechtnis": {"correct": 0, "total": 0, "score": 0.0},
    }

    # Build answer lookup
    answer_map = {a["question_id"]: a for a in answers}

    for q in questions:
        qid = q["id"]
        kategorie = q.get("kategorie", "logik")
        difficulty = q.get("schwierigkeit", 0.5)
        time_limit = q.get("zeit_sekunden", 60)

        max_possible += difficulty * 1.2  # max with time bonus

        if kategorie not in kategorie_scores:
            kategorie_scores[kategorie] = {"correct": 0, "total": 0, "score": 0.0}
        kategorie_scores[kategorie]["total"] += 1

        if qid in answer_map:
            user_answer = answer_map[qid]
            if user_answer["answer"] == q["correct"]:
                # Time bonus: faster = more points
                time_taken = user_answer.get("time_seconds", time_limit)
                time_ratio = time_limit / max(time_taken, 1)
                bonus = min(0.2, time_ratio * 0.05)
                points = difficulty * (1.0 + bonus)
                raw_score += points
                kategorie_scores[kategorie]["correct"] += 1
                kategorie_scores[kategorie]["score"] += points

    # Normalize to percentile
    if max_possible > 0:
        percentile = raw_score / max_possible
    else:
        percentile = 0.5

    # Clamp percentile to avoid extreme values
    percentile = max(0.02, min(0.98, percentile))

    # Convert to IQ using inverse normal CDF
    z_score = _norm_ppf(percentile)
    iq = round(100 + 15 * z_score)
    iq = max(70, min(145, iq))

    # Calculate category percentages
    kategorie_prozent = {}
    staerken = []
    schwaechen = []
    for kat, data in kategorie_scores.items():
        if data["total"] > 0:
            pct = round(data["correct"] / data["total"] * 100)
            kategorie_prozent[kat] = pct
            if pct >= 75:
                staerken.append(kat)
            elif pct < 50:
                schwaechen.append(kat)

    overall_percentile = round(_norm_cdf(z_score) * 100)

    return {
        "iq": iq,
        "iq_range": f"{iq - 5} - {iq + 5}",
        "percentile": overall_percentile,
        "klassifikation": _get_iq_classification(iq),
        "kategorien": kategorie_prozent,
        "staerken": staerken,
        "schwaechen": schwaechen,
        "vergleich": f"Besser als {overall_percentile}% der Bevölkerung",
        "raw_score": round(raw_score, 2),
        "max_score": round(max_possible, 2),
    }


@router.post("/generieren")
async def generate_iq_test(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate a new IQ test with 40 questions across 5 categories.

    Users can only take the test once per 30 days.
    """
    user_id = current_user["id"]

    # Check if user has taken test recently (30-day cooldown)
    try:
        cursor = await db.execute(
            "SELECT created_at FROM iq_results WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        last_test = await cursor.fetchone()
        if last_test:
            last_date = datetime.fromisoformat(dict(last_test)["created_at"])
            if datetime.now() - last_date < timedelta(days=30):
                days_left = 30 - (datetime.now() - last_date).days
                raise HTTPException(
                    status_code=429,
                    detail=f"Du kannst den IQ-Test nur alle 30 Tage machen. Noch {days_left} Tage warten.",
                )
    except HTTPException:
        raise
    except Exception:
        pass  # Table may not exist yet

    # Generate questions via Groq
    prompt = """Erstelle einen wissenschaftlich validen IQ-Test mit genau 40 Fragen.

KATEGORIEN (8 Fragen je Kategorie):

1. LOGIK (kategorie: "logik"):
- Zahlenreihen: "2, 4, 8, 16, ?" → Antwort: 32
- Buchstabenmuster: "A, C, E, G, ?" → Antwort: I
- Logische Schlüsse: "Alle Äpfel sind Früchte. Manche Früchte sind rot. Welche Aussage stimmt?"

2. VERBAL (kategorie: "verbal"):
- Analogien: "Arzt:Krankenhaus = Lehrer:?" → Schule
- Wortbedeutungen: "Welches Wort passt NICHT? Fröhlich, Heiter, Traurig, Lustig"
- Sprachliche Logik: "Wenn A vor B kommt und B vor C..."

3. MATHE (kategorie: "mathe"):
- Rechenlogik OHNE Schulwissen: "3 Maler brauchen 6 Stunden. Wie lange brauchen 6 Maler?"
- Verhältnisse: "Ein Kuchen wird in 8 Stücke geteilt. Max isst 3, Lisa 2. Wie viel bleibt?"
- Wahrscheinlichkeit: "In einer Schublade sind 5 rote und 3 blaue Socken..."

4. RAUM (kategorie: "raum"):
- Würfel-Rotation (textbasiert): "Ein Würfel zeigt oben 6, vorne 2. Er kippt nach rechts. Was zeigt oben?"
- Spiegelungen: "Welches Wort sieht gespiegelt gleich aus? AUTO, MAMA, OTTO, HAUS"
- Muster-Ergänzung: "Welche Form ergänzt das Muster?"

5. GEDÄCHTNIS (kategorie: "gedaechtnis"):
- Zahlenfolgen: "Merke: 7-3-9-1-5. Welche Zahl kommt an Position 3?"
- Textverständnis: "Lies den folgenden Absatz... Was war die Farbe des Hauses?"
- Reihenfolge: "Anna ist größer als Ben, Ben ist größer als Clara. Wer ist am kleinsten?"

REGELN:
- KEIN Schulwissen nötig (IQ misst Intelligenz, nicht Wissen)
- Jede Frage hat genau 4 Optionen (A, B, C, D)
- Genau 1 richtige Antwort pro Frage
- Schwierigkeit variiert: 0.3 (leicht) bis 0.9 (sehr schwer)
- Zeitlimit pro Frage: 45-90 Sekunden
- Mische leichte und schwere Fragen innerhalb jeder Kategorie

FORMAT: Antworte NUR mit JSON-Array, kein anderer Text:
[{"id": 1, "kategorie": "logik", "frage": "Welche Zahl kommt als nächstes? 2, 4, 8, 16, ?", "optionen": ["24", "32", "30", "28"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.4}]

Erstelle genau 40 Fragen (8 pro Kategorie), aufsteigend nummeriert von 1-40."""

    try:
        response = call_groq_llm(
            prompt=prompt,
            system_prompt="Du bist ein Experte für psychometrische Tests und IQ-Test-Erstellung. Antworte NUR mit validem JSON.",
            subject="general",
            level="advanced",
            language="de",
            is_pro=True,
            temperature_override=0.1,
        )

        # Parse JSON from response
        questions = _parse_json_response(response)

        if not questions or len(questions) < 20:
            # Fallback to hardcoded sample questions
            questions = _get_fallback_questions()

    except Exception as e:
        logger.warning("IQ test generation via Groq failed: %s, using fallback", e)
        questions = _get_fallback_questions()

    # Ensure all questions have required fields
    for i, q in enumerate(questions):
        q.setdefault("id", i + 1)
        q.setdefault("kategorie", ["logik", "verbal", "mathe", "raum", "gedaechtnis"][i % 5])
        q.setdefault("zeit_sekunden", 60)
        q.setdefault("schwierigkeit", 0.5)
        if "correct" not in q:
            q["correct"] = 0

    # Save test to DB
    cursor = await db.execute(
        """INSERT INTO iq_tests (user_id, questions, num_questions, time_limit_seconds, status)
        VALUES (?, ?, ?, ?, 'active')""",
        (user_id, json.dumps(questions, ensure_ascii=False), len(questions), 2700),
    )
    await db.commit()
    test_id = cursor.lastrowid

    # Return questions WITHOUT correct answers
    safe_questions = []
    for q in questions:
        safe_questions.append({
            "id": q["id"],
            "kategorie": q["kategorie"],
            "frage": q["frage"],
            "optionen": q["optionen"],
            "zeit_sekunden": q["zeit_sekunden"],
            "schwierigkeit": q["schwierigkeit"],
        })

    return {
        "test_id": test_id,
        "questions": safe_questions,
        "num_questions": len(safe_questions),
        "time_limit_seconds": 2700,  # 45 minutes
        "kategorien": ["logik", "verbal", "mathe", "raum", "gedaechtnis"],
    }


@router.post("/berechnen")
async def submit_iq_test(
    submission: IQTestSubmission,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit IQ test answers and calculate score."""
    user_id = current_user["id"]

    # Get the test
    cursor = await db.execute(
        "SELECT * FROM iq_tests WHERE id = ? AND user_id = ? AND status = 'active'",
        (submission.test_id, user_id),
    )
    test_row = await cursor.fetchone()
    if not test_row:
        raise HTTPException(status_code=404, detail="Test nicht gefunden oder bereits abgegeben.")

    test = dict(test_row)
    questions = json.loads(test["questions"])

    # Convert answers to dicts
    answers_dicts = [
        {"question_id": a.question_id, "answer": a.answer, "time_seconds": a.time_seconds}
        for a in submission.answers
    ]

    # Calculate IQ
    result = _calculate_iq(answers_dicts, questions)

    # Update test status
    await db.execute(
        "UPDATE iq_tests SET status = 'completed', submitted_at = datetime('now') WHERE id = ?",
        (submission.test_id,),
    )

    # Save result
    await db.execute(
        """INSERT INTO iq_results (user_id, test_id, iq_score, iq_range, percentile,
        klassifikation, kategorien, staerken, schwaechen, raw_score, max_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            submission.test_id,
            result["iq"],
            result["iq_range"],
            result["percentile"],
            result["klassifikation"],
            json.dumps(result["kategorien"]),
            json.dumps(result["staerken"]),
            json.dumps(result["schwaechen"]),
            result["raw_score"],
            result["max_score"],
        ),
    )
    await db.commit()

    # Award gamification XP
    try:
        from app.routes.gamification import add_xp
        await add_xp(user_id, 25, "iq_test", db)
    except Exception:
        pass

    return result


@router.get("/ergebnis")
async def get_iq_result(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get the user's latest IQ test result."""
    user_id = current_user["id"]

    try:
        cursor = await db.execute(
            """SELECT iq_score, iq_range, percentile, klassifikation,
            kategorien, staerken, schwaechen, raw_score, max_score, created_at
            FROM iq_results WHERE user_id = ? ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        )
        row = await cursor.fetchone()
    except Exception:
        row = None

    if not row:
        return {"has_result": False}

    r = dict(row)
    return {
        "has_result": True,
        "iq": r["iq_score"],
        "iq_range": r["iq_range"],
        "percentile": r["percentile"],
        "klassifikation": r["klassifikation"],
        "kategorien": json.loads(r["kategorien"]) if r["kategorien"] else {},
        "staerken": json.loads(r["staerken"]) if r["staerken"] else [],
        "schwaechen": json.loads(r["schwaechen"]) if r["schwaechen"] else [],
        "raw_score": r["raw_score"],
        "max_score": r["max_score"],
        "test_date": r["created_at"],
    }


@router.get("/cooldown")
async def check_cooldown(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Check if the user can take the IQ test (30-day cooldown)."""
    user_id = current_user["id"]

    try:
        cursor = await db.execute(
            "SELECT created_at FROM iq_results WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
    except Exception:
        return {"can_take_test": True, "days_remaining": 0}

    if not row:
        return {"can_take_test": True, "days_remaining": 0}

    last_date = datetime.fromisoformat(dict(row)["created_at"])
    diff = datetime.now() - last_date
    if diff >= timedelta(days=30):
        return {"can_take_test": True, "days_remaining": 0}

    days_left = 30 - diff.days
    return {"can_take_test": False, "days_remaining": days_left}


def _parse_json_response(response: str) -> list[dict]:
    """Extract JSON array from LLM response."""
    # Try to find JSON array in response
    text = response.strip()

    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Find array bounds
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return []


def _get_fallback_questions() -> list[dict]:
    """Fallback IQ test questions when Groq is unavailable."""
    questions = [
        # LOGIK (8)
        {"id": 1, "kategorie": "logik", "frage": "Welche Zahl kommt als nächstes? 2, 4, 8, 16, ?", "optionen": ["24", "32", "30", "28"], "correct": 1, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 2, "kategorie": "logik", "frage": "Welcher Buchstabe kommt als nächstes? A, C, E, G, ?", "optionen": ["H", "I", "J", "K"], "correct": 1, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 3, "kategorie": "logik", "frage": "Welche Zahl kommt als nächstes? 1, 1, 2, 3, 5, 8, ?", "optionen": ["11", "12", "13", "14"], "correct": 2, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 4, "kategorie": "logik", "frage": "Wenn alle Rosen Blumen sind und manche Blumen schnell welken, welche Aussage stimmt?", "optionen": ["Alle Rosen welken schnell", "Manche Rosen könnten schnell welken", "Keine Rose welkt schnell", "Rosen sind keine Blumen"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 5, "kategorie": "logik", "frage": "Welche Zahl kommt als nächstes? 3, 6, 11, 18, 27, ?", "optionen": ["36", "38", "35", "40"], "correct": 1, "zeit_sekunden": 75, "schwierigkeit": 0.7},
        {"id": 6, "kategorie": "logik", "frage": "Wenn X > Y und Y > Z, was stimmt?", "optionen": ["Z > X", "X = Z", "X > Z", "Y > X"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 7, "kategorie": "logik", "frage": "Welche Zahl passt nicht in die Reihe? 2, 3, 5, 7, 9, 11", "optionen": ["2", "3", "9", "11"], "correct": 2, "zeit_sekunden": 60, "schwierigkeit": 0.6},
        {"id": 8, "kategorie": "logik", "frage": "Welche Zahl kommt als nächstes? 1, 4, 9, 16, 25, ?", "optionen": ["30", "36", "35", "49"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        # VERBAL (8)
        {"id": 9, "kategorie": "verbal", "frage": "Arzt : Krankenhaus = Lehrer : ?", "optionen": ["Patient", "Schule", "Buch", "Wissen"], "correct": 1, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 10, "kategorie": "verbal", "frage": "Welches Wort passt NICHT? Fröhlich, Heiter, Traurig, Lustig", "optionen": ["Fröhlich", "Heiter", "Traurig", "Lustig"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 11, "kategorie": "verbal", "frage": "Finger : Hand = Zeh : ?", "optionen": ["Arm", "Bein", "Fuß", "Knie"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 12, "kategorie": "verbal", "frage": "Welches Wort hat die ähnlichste Bedeutung wie 'mutig'?", "optionen": ["Ängstlich", "Tapfer", "Klug", "Schnell"], "correct": 1, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 13, "kategorie": "verbal", "frage": "Vogel : Nest = Mensch : ?", "optionen": ["Baum", "Haus", "Auto", "Schule"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 14, "kategorie": "verbal", "frage": "Welches Wort passt NICHT? Hammer, Schraubenzieher, Nagel, Zange", "optionen": ["Hammer", "Schraubenzieher", "Nagel", "Zange"], "correct": 2, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 15, "kategorie": "verbal", "frage": "Dunkel : Hell = Kalt : ?", "optionen": ["Eis", "Nacht", "Warm", "Regen"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.4},
        {"id": 16, "kategorie": "verbal", "frage": "Welches Wort hat die gegenteilige Bedeutung von 'großzügig'?", "optionen": ["Reich", "Geizig", "Freundlich", "Groß"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        # MATHE (8)
        {"id": 17, "kategorie": "mathe", "frage": "3 Maler brauchen 6 Stunden für ein Haus. Wie lange brauchen 6 Maler?", "optionen": ["12 Stunden", "3 Stunden", "2 Stunden", "9 Stunden"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.4},
        {"id": 18, "kategorie": "mathe", "frage": "Ein Kuchen wird in 8 Stücke geteilt. Max isst 3, Lisa 2. Wie viel Prozent bleiben übrig?", "optionen": ["25%", "37,5%", "50%", "62,5%"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 19, "kategorie": "mathe", "frage": "Wenn du 100€ hast und 30% ausgibst, wie viel bleibt?", "optionen": ["30€", "60€", "70€", "80€"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 20, "kategorie": "mathe", "frage": "Ein Zug fährt 120 km in 2 Stunden. Wie weit kommt er in 30 Minuten?", "optionen": ["20 km", "30 km", "40 km", "60 km"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.4},
        {"id": 21, "kategorie": "mathe", "frage": "Wenn 5 Äpfel 3€ kosten, wie viel kosten 15 Äpfel?", "optionen": ["6€", "9€", "12€", "15€"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.4},
        {"id": 22, "kategorie": "mathe", "frage": "In einer Schublade sind 5 rote und 3 blaue Socken. Wie viele musst du blind ziehen, um sicher 2 gleiche zu haben?", "optionen": ["2", "3", "4", "5"], "correct": 1, "zeit_sekunden": 75, "schwierigkeit": 0.7},
        {"id": 23, "kategorie": "mathe", "frage": "Wenn ein Hemd 40€ kostet und 25% reduziert ist, was war der Originalpreis?", "optionen": ["50€", "53,33€", "55€", "60€"], "correct": 1, "zeit_sekunden": 75, "schwierigkeit": 0.6},
        {"id": 24, "kategorie": "mathe", "frage": "Peter ist doppelt so alt wie Maria. In 10 Jahren ist Peter 1,5-mal so alt. Wie alt ist Maria jetzt?", "optionen": ["10", "15", "20", "25"], "correct": 2, "zeit_sekunden": 90, "schwierigkeit": 0.8},
        # RAUM (8)
        {"id": 25, "kategorie": "raum", "frage": "Welches Wort sieht horizontal gespiegelt gleich aus?", "optionen": ["AUTO", "MAMA", "OTTO", "HAUS"], "correct": 2, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 26, "kategorie": "raum", "frage": "Ein Quadrat hat 4 Ecken. Wenn man eine Ecke abschneidet, wie viele Ecken hat die neue Form?", "optionen": ["3", "4", "5", "6"], "correct": 2, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 27, "kategorie": "raum", "frage": "Wie viele Würfel braucht man für einen 3x3x3-Würfel?", "optionen": ["9", "18", "27", "36"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.4},
        {"id": 28, "kategorie": "raum", "frage": "Ein Dreieck wird um 180° gedreht. Was ändert sich?", "optionen": ["Die Form", "Die Größe", "Die Ausrichtung", "Nichts"], "correct": 2, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 29, "kategorie": "raum", "frage": "Wie viele Flächen hat ein Würfel?", "optionen": ["4", "6", "8", "12"], "correct": 1, "zeit_sekunden": 30, "schwierigkeit": 0.2},
        {"id": 30, "kategorie": "raum", "frage": "Wenn man einen Kreis in der Mitte faltet, welche Form entsteht?", "optionen": ["Dreieck", "Rechteck", "Halbkreis", "Quadrat"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 31, "kategorie": "raum", "frage": "Ein Würfel zeigt oben 1, vorne 2. Welche Zahl ist unten?", "optionen": ["3", "4", "5", "6"], "correct": 3, "zeit_sekunden": 75, "schwierigkeit": 0.7},
        {"id": 32, "kategorie": "raum", "frage": "Wie viele Symmetrieachsen hat ein Quadrat?", "optionen": ["1", "2", "4", "8"], "correct": 2, "zeit_sekunden": 60, "schwierigkeit": 0.6},
        # GEDÄCHTNIS (8)
        {"id": 33, "kategorie": "gedaechtnis", "frage": "Merke: 7-3-9-1-5. Welche Zahl steht an Position 3?", "optionen": ["7", "3", "9", "1"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.4},
        {"id": 34, "kategorie": "gedaechtnis", "frage": "Merke: Rot-Blau-Grün-Gelb-Weiß. Welche Farbe kommt nach Grün?", "optionen": ["Rot", "Blau", "Gelb", "Weiß"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.3},
        {"id": 35, "kategorie": "gedaechtnis", "frage": "Anna ist größer als Ben, Ben ist größer als Clara, Clara ist größer als David. Wer ist am kleinsten?", "optionen": ["Anna", "Ben", "Clara", "David"], "correct": 3, "zeit_sekunden": 60, "schwierigkeit": 0.4},
        {"id": 36, "kategorie": "gedaechtnis", "frage": "Merke: 4-8-2-6-1-9. Was ist die Summe der ersten drei Zahlen?", "optionen": ["12", "14", "16", "18"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 37, "kategorie": "gedaechtnis", "frage": "Merke: Hund-Katze-Maus-Vogel-Fisch. Welches Tier kommt VOR dem Vogel?", "optionen": ["Hund", "Katze", "Maus", "Fisch"], "correct": 2, "zeit_sekunden": 45, "schwierigkeit": 0.4},
        {"id": 38, "kategorie": "gedaechtnis", "frage": "Tom hat 3 Äpfel, gibt 1 an Lisa, bekommt 2 von Max, gibt 2 an Julia. Wie viele hat Tom?", "optionen": ["1", "2", "3", "4"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.5},
        {"id": 39, "kategorie": "gedaechtnis", "frage": "Merke: 5-2-8-4-7-1-6-3. Welche Zahl steht an Position 6?", "optionen": ["7", "1", "4", "6"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.6},
        {"id": 40, "kategorie": "gedaechtnis", "frage": "In einem Raum sind 3 Lampen. Lampe 1 ist an, Lampe 2 aus, Lampe 3 an. Du schaltest 1 aus und 2 an. Welche sind jetzt an?", "optionen": ["1 und 3", "2 und 3", "1 und 2", "Alle"], "correct": 1, "zeit_sekunden": 60, "schwierigkeit": 0.5},
    ]
    return questions
