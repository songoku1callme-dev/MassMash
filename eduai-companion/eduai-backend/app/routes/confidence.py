"""Confidence Tracking + Blind-Spot Detection + Auto-Feedback Loop.

Block C: Confidence nach Quiz-Antworten tracken, Blind-Spots erkennen.
Block D: Auto-Feedback Loop — Wissenslücken analysieren + Karteikarten erstellen.
"""
import json
import logging
import os
import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quiz", tags=["confidence"])


async def _insert_flashcard(
    db: aiosqlite.Connection,
    *,
    user_id: int,
    subject: str,
    front: str,
    back: str,
    deck_name: str,
) -> None:
    """Insert flashcard compatible with both schemas.

    Some DBs use (user_id, subject, front, back), others use decks with deck_id.
    """
    cols_cur = await db.execute("PRAGMA table_info(flashcards)")
    cols_rows = await cols_cur.fetchall()
    cols = {dict(r).get("name") for r in cols_rows}

    if "deck_id" in cols:
        # Ensure deck table exists
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

    # Legacy schema
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
# Request Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConfidenceRequest(BaseModel):
    confidence: int  # 1-5
    war_richtig: bool
    quiz_id: Optional[int] = None
    fach: str = "Allgemein"
    thema: str = ""


class SessionEndRequest(BaseModel):
    fach: str = "Allgemein"
    antworten: list[dict] = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Block C: Confidence Tracking
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/confidence")
async def track_confidence(
    req: ConfidenceRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Speichert Confidence-Level nach Quiz-Antwort + erkennt Blind Spots."""
    user_id = current_user["id"]

    # Blind-Spot Erkennung: Hohe Confidence + Falsch = Blind Spot
    is_blind_spot = req.confidence >= 4 and not req.war_richtig

    # In DB speichern
    try:
        await db.execute(
            """INSERT INTO quiz_confidence
            (user_id, quiz_id, fach, thema, confidence, war_richtig, blind_spot)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, req.quiz_id, req.fach, req.thema,
             req.confidence, int(req.war_richtig), int(is_blind_spot)),
        )
        await db.commit()
    except Exception as e:
        logger.warning("Confidence tracking DB error (non-fatal): %s", e)

    # Bei Blind Spot: KI generiert gezielte Karteikarten
    if is_blind_spot:
        try:
            groq_key = os.getenv("GROQ_API_KEY", "")
            if groq_key:
                from groq import Groq
                client = Groq(api_key=groq_key)
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content":
                        f"Erstelle 2 Karteikarten die den häufigsten Irrtum "
                        f"bei '{req.thema}' in {req.fach} korrigieren.\n"
                        f"JSON: [{{\"frage\":\"...\",\"antwort\":\"...\"}}]\n"
                        f"Echte Umlaute: ä ö ü ß."
                    }],
                    temperature=0.4, max_tokens=200,
                )
                raw = resp.choices[0].message.content or ""
                match = re.search(r'\[.*\]', raw, re.DOTALL)
                if match:
                    karten = json.loads(match.group())
                    for k in karten[:2]:
                        if isinstance(k, dict) and "frage" in k and "antwort" in k:
                            await _insert_flashcard(
                                db,
                                user_id=user_id,
                                subject=req.fach,
                                front=k["frage"],
                                back=k["antwort"],
                                deck_name="Blind Spots",
                            )
        except Exception as e:
            logger.warning("Blind-spot Karteikarten failed (non-fatal): %s", e)

    return {"blind_spot": is_blind_spot, "confidence": req.confidence}


@router.get("/blind-spots")
async def get_blind_spots(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Gibt Blind-Spot Heatmap-Daten zurück (Fächer mit hoher Fehlquote trotz Confidence)."""
    user_id = current_user["id"]

    try:
        cursor = await db.execute(
            """SELECT fach, COUNT(*) as blind_spots
            FROM quiz_confidence
            WHERE user_id = ? AND blind_spot = 1
            GROUP BY fach
            ORDER BY blind_spots DESC""",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return {
            "fächer": [{"fach": dict(r)["fach"], "blind_spots": dict(r)["blind_spots"]} for r in rows]
        }
    except Exception:
        return {"fächer": []}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Block D: Auto-Feedback Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/session-end")
async def quiz_session_end(
    req: SessionEndRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Nach jeder Quiz-Session:
    1. 3 größte Wissenslücken analysieren
    2. Sofort 5 Karteikarten erstellen
    3. Im User-Memory speichern
    """
    user_id = current_user["id"]
    falsche = [a for a in req.antworten if not a.get("richtig", False)]

    if not falsche:
        return {"lücken": [], "karteikarten": 0}

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return {"lücken": [], "karteikarten": 0, "hinweis": "Kein API-Key konfiguriert"}

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)

        # Klasse und Bundesland laden
        klasse = current_user.get("school_grade", "10")
        bundesland = ""
        try:
            bl_cursor = await db.execute(
                "SELECT bundesland FROM users WHERE id = ?", (user_id,)
            )
            bl_row = await bl_cursor.fetchone()
            bundesland = dict(bl_row).get("bundesland", "") if bl_row else ""
        except Exception:
            pass

        analyse = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content":
                f"Analysiere diese falschen Antworten in {req.fach}:\n"
                + "\n".join([f"- Frage: {a.get('frage', '')} | Schüler: {a.get('schüler_antwort', a.get('antwort', ''))}"
                             for a in falsche[:10]])
                + f"\n\nKlasse {klasse}, {bundesland}.\n\n"
                + "Identifiziere die 3 GRUNDLEGENDEN Wissenslücken "
                + "(nicht Symptome, sondern Ursachen).\n"
                + "Erstelle sofort 5 Karteikarten die diese Lücken schließen.\n\n"
                + "JSON-Format:\n"
                + "{\n"
                + '  "lücken": ["Lücke 1","Lücke 2","Lücke 3"],\n'
                + '  "karteikarten": [{"frage":"...","antwort":"..."}]\n'
                + "}\n"
                + "Echte Umlaute: ä ö ü ß."
            }],
            temperature=0.4, max_tokens=600,
        )

        text = analyse.choices[0].message.content or ""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        data = json.loads(match.group()) if match else {}

        # Karteikarten speichern
        karten = data.get("karteikarten", [])
        karten_count = 0
        for k in karten[:5]:
            if isinstance(k, dict) and "frage" in k and "antwort" in k:
                await _insert_flashcard(
                    db,
                    user_id=user_id,
                    subject=req.fach,
                    front=k["frage"],
                    back=k["antwort"],
                    deck_name="Auto-Feedback",
                )
                karten_count += 1

        return {
            "lücken": data.get("lücken", []),
            "karteikarten": karten_count,
        }
    except Exception as e:
        logger.error("Auto-Feedback Loop failed: %s", e)
        return {"lücken": [], "karteikarten": 0, "error": str(e)}
