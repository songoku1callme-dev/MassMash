"""Voice Exam routes — Mündliche Prüfung mit STT/TTS und KI-Bewertung.

Block B: 6 Fragen, Groq-basierte Bewertung, Auto-Karteikarten bei Fehlern.
"""
import json
import logging
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.ai_engine import normalize_fach

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exam", tags=["voice_exam"])


async def _insert_flashcard(
    db: aiosqlite.Connection,
    *,
    user_id: int,
    subject: str,
    front: str,
    back: str,
    deck_name: str,
) -> None:
    """Insert flashcard compatible with both schemas."""
    cols_cur = await db.execute("PRAGMA table_info(flashcards)")
    cols_rows = await cols_cur.fetchall()
    cols = {dict(r).get("name") for r in cols_rows}

    if "deck_id" in cols:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS flashcard_decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                subject TEXT DEFAULT 'general',
                description TEXT DEFAULT '',
                card_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )"""
        )
        await db.commit()

        deck_cur = await db.execute(
            "SELECT id FROM flashcard_decks WHERE user_id = ? AND name = ?",
            (user_id, deck_name),
        )
        deck_row = await deck_cur.fetchone()
        if deck_row:
            deck_id = dict(deck_row)["id"]
        else:
            cur = await db.execute(
                "INSERT INTO flashcard_decks (user_id, name, subject) VALUES (?, ?, ?)",
                (user_id, deck_name, subject),
            )
            await db.commit()
            deck_id = cur.lastrowid

        await db.execute(
            "INSERT INTO flashcards (deck_id, user_id, front, back) VALUES (?, ?, ?, ?)",
            (deck_id, user_id, front, back),
        )
        try:
            await db.execute(
                "UPDATE flashcard_decks SET card_count = card_count + 1 WHERE id = ?",
                (deck_id,),
            )
        except Exception:
            pass
        await db.commit()
        return

    if {"user_id", "front", "back"}.issubset(cols):
        if "subject" in cols:
            await db.execute(
                "INSERT INTO flashcards (user_id, subject, front, back) VALUES (?, ?, ?, ?)",
                (user_id, subject, front, back),
            )
        else:
            await db.execute(
                "INSERT INTO flashcards (user_id, front, back) VALUES (?, ?, ?)",
                (user_id, front, back),
            )
        await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompts für Prüfer und Bewerter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXAMINER_PROMPT = """Du bist ein freundlicher aber professioneller mündlicher Prüfer
für das Fach {fach} in {bundesland}, Klasse {klasse}.

Stelle EINE klare, prüfungsrelevante Frage.
Die Frage muss zum Lehrplan passen und altersgerecht sein.

REGELN:
- NUR die Frage stellen, KEIN anderer Text
- Echte Umlaute: ä ö ü ß
- Fachbegriffe verwenden aber verständlich
- Schwierigkeitsgrad: mittelschwer bis schwer
- KEINE Multiple-Choice, nur offene Fragen

Bisherige Fragen (nicht wiederholen):
{bisherige}
"""

EVALUATOR_PROMPT = """Du bist ein fairer Prüfer für das Fach {fach}.
Bewerte die Antwort des Schülers auf die gestellte Frage.

Frage: {frage}
Antwort des Schülers: {antwort}

WICHTIG: Die Antwort kam per Spracherkennung — ignoriere kleine
Verschreiber/Hörfehler und bewerte NUR den FACHLICHEN Inhalt.

Antworte AUSSCHLIESSLICH mit diesem JSON (kein anderer Text):
{{
  "bewertung": "richtig" | "teilweise" | "falsch",
  "score": 0-10,
  "feedback": "Kurze schriftliche Rückmeldung (2-3 Sätze)",
  "feedback_gesprochen": "Mündliches Feedback das vorgelesen wird (1-2 Sätze, ermutigend)"
}}

Echte Umlaute verwenden: ä ö ü ß
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Request/Response Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExamStartRequest(BaseModel):
    fach: str = "Mathematik"
    klasse: str = "10"
    bundesland: str = "Bayern"


class ExamEvalRequest(BaseModel):
    fach: str
    frage: str
    antwort: str


class ExamNextRequest(BaseModel):
    fach: str
    verlauf: list[dict] = []
    frage_nr: int = 2
    klasse: str = "10"
    bundesland: str = "Bayern"


class ExamFinishRequest(BaseModel):
    fach: str
    verlauf: list[dict] = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Hilfsfunktion: Groq aufrufen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _call_groq(system: str, user_msg: str, temperature: float = 0.7, max_tokens: int = 300) -> str:
    """Synchroner Groq-Aufruf für Exam-Routen."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise HTTPException(status_code=503, detail="Kein GROQ_API_KEY konfiguriert")
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("Groq exam call failed: %s", e)
        raise HTTPException(status_code=500, detail=f"KI-Fehler: {str(e)}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Routen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/start")
async def exam_start(
    req: ExamStartRequest,
    current_user: dict = Depends(get_current_user),
):
    """Startet mündliche Prüfung — gibt erste Frage + Begrüßung zurück."""
    fach = normalize_fach(req.fach)

    greeting = (
        f"Willkommen zur mündlichen Prüfung in {fach}! "
        f"Ich stelle dir 6 Fragen. Nimm dir Zeit und antworte in ganzen Sätzen. "
        f"Los geht's!"
    )

    prompt = EXAMINER_PROMPT.format(
        fach=fach, bundesland=req.bundesland, klasse=req.klasse, bisherige="(keine)"
    )
    frage = _call_groq(prompt, f"Stelle die erste Prüfungsfrage in {fach}.", temperature=0.8)

    return {
        "greeting": greeting,
        "frage": frage.strip(),
        "fach": fach,
        "frage_nr": 1,
    }


@router.post("/evaluate")
async def exam_evaluate(
    req: ExamEvalRequest,
    current_user: dict = Depends(get_current_user),
):
    """Bewertet eine Schüler-Antwort und gibt Feedback."""
    fach = normalize_fach(req.fach)

    prompt = EVALUATOR_PROMPT.format(
        fach=fach, frage=req.frage, antwort=req.antwort
    )
    raw = _call_groq(
        "Du bist ein JSON-Generator. Antworte NUR mit validem JSON.",
        prompt,
        temperature=0.3,
        max_tokens=300,
    )

    # JSON extrahieren
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            data = {
                "bewertung": "teilweise",
                "score": 5,
                "feedback": "Konnte die Antwort nicht vollständig bewerten.",
                "feedback_gesprochen": "Danke für deine Antwort! Lass uns weitermachen.",
            }
    except json.JSONDecodeError:
        data = {
            "bewertung": "teilweise",
            "score": 5,
            "feedback": raw[:200],
            "feedback_gesprochen": "Danke für deine Antwort!",
        }

    return data


@router.post("/next")
async def exam_next(
    req: ExamNextRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generiert die nächste Prüfungsfrage basierend auf bisherigem Verlauf."""
    fach = normalize_fach(req.fach)

    bisherige = "\n".join([
        f"- Frage {i+1}: {v.get('frage', '')}" for i, v in enumerate(req.verlauf)
    ]) or "(keine)"

    prompt = EXAMINER_PROMPT.format(
        fach=fach, bundesland=req.bundesland, klasse=req.klasse, bisherige=bisherige
    )
    frage = _call_groq(
        prompt,
        f"Stelle Frage {req.frage_nr} von 6 in {fach}. Thematisch anders als bisherige.",
        temperature=0.8,
    )

    return {
        "frage": frage.strip(),
        "frage_nr": req.frage_nr,
    }


@router.post("/finish")
async def exam_finish(
    req: ExamFinishRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Beendet die Prüfung — berechnet Note, erstellt Karteikarten aus Fehlern."""
    fach = normalize_fach(req.fach)
    user_id = current_user["id"]

    # Gesamtscore berechnen
    total_score = 0
    total_questions = len(req.verlauf)
    fehler = []
    stärken = []

    for v in req.verlauf:
        score = v.get("score", 0)
        total_score += score
        if score <= 4:
            fehler.append(v.get("frage", ""))
        elif score >= 7:
            stärken.append(v.get("frage", ""))

    avg_score = total_score / max(total_questions, 1)

    # Deutsche Schulnote berechnen (1-6)
    if avg_score >= 9:
        note = 1
    elif avg_score >= 7.5:
        note = 2
    elif avg_score >= 6:
        note = 3
    elif avg_score >= 4:
        note = 4
    elif avg_score >= 2:
        note = 5
    else:
        note = 6

    # Karteikarten aus Fehlern erstellen
    karten_erstellt = 0
    if fehler:
        try:
            karten_prompt = (
                f"Erstelle {min(len(fehler), 5)} Karteikarten für die Themen "
                f"bei denen der Schüler in {fach} Schwierigkeiten hatte:\n"
                + "\n".join([f"- {f}" for f in fehler[:5]])
                + "\n\nJSON-Format: [{\"frage\":\"...\",\"antwort\":\"...\"}]\n"
                "Echte Umlaute: ä ö ü ß."
            )
            raw = _call_groq(
                "Du bist ein JSON-Generator. Antworte NUR mit validem JSON-Array.",
                karten_prompt,
                temperature=0.4,
                max_tokens=500,
            )
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                karten = json.loads(match.group())
                for k in karten[:5]:
                    if isinstance(k, dict) and "frage" in k and "antwort" in k:
                        await _insert_flashcard(
                            db,
                            user_id=user_id,
                            subject=fach,
                            front=k["frage"],
                            back=k["antwort"],
                            deck_name="Mündliche Prüfung",
                        )
                        karten_erstellt += 1
        except Exception as e:
            logger.warning("Karteikarten-Erstellung fehlgeschlagen: %s", e)

    # XP vergeben
    try:
        from app.routes.gamification import add_xp
        xp_amount = 20 + (10 if note <= 2 else 5 if note <= 3 else 0)
        await add_xp(user_id, xp_amount, "voice_exam", db)
    except Exception:
        pass

    return {
        "note": note,
        "avg_score": round(avg_score, 1),
        "total_score": total_score,
        "total_questions": total_questions,
        "stärken": stärken[:3],
        "schwächen": fehler[:3],
        "karteikarten_erstellt": karten_erstellt,
        "feedback": (
            f"Deine Note: {note} ({round(avg_score, 1)}/10 Punkte). "
            + ("Hervorragend! " if note <= 2 else "Gut gemacht! " if note <= 3 else "Weiter üben! ")
            + (f"{karten_erstellt} Karteikarten wurden aus deinen Fehlern erstellt." if karten_erstellt > 0 else "")
        ),
    }
