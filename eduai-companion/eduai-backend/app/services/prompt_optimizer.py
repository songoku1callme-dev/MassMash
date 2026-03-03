"""
Auto-Prompt-Tuning — KI analysiert negatives Feedback,
erkennt Muster, generiert verbesserte System-Prompts.
Admin genehmigt → neuer Prompt wird aktiv.
"""
import os
import json
import logging
from datetime import datetime, timedelta

import aiosqlite
import httpx

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Aktive Prompts pro Fach (werden aus DB geladen)
AKTIVE_PROMPTS: dict[str, str] = {}


async def load_approved_prompts():
    """Lädt alle genehmigten Prompts aus der DB."""
    db_path = os.getenv("DATABASE_PATH", "app.db")
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT fach, neuer_prompt FROM prompt_vorschlaege
                WHERE status = 'genehmigt'
                ORDER BY genehmigt_am DESC"""
            )
            rows = await cursor.fetchall()
            for row in rows:
                rd = dict(row)
                fach = rd.get("fach", "")
                if fach and fach not in AKTIVE_PROMPTS:
                    AKTIVE_PROMPTS[fach] = rd.get("neuer_prompt", "")
            logger.info("Geladene Prompts: %d Fächer", len(AKTIVE_PROMPTS))
    except Exception as e:
        logger.warning("Prompts laden fehlgeschlagen: %s", e)


def get_prompt_for_fach(fach: str, default_prompt: str) -> str:
    """Gibt den aktiven Prompt für ein Fach zurück (oder Default)."""
    return AKTIVE_PROMPTS.get(fach, default_prompt)


async def _groq_generate(prompt: str, max_tokens: int = 600,
                          temperature: float = 0.3) -> str:
    """Groq API call helper."""
    if not GROQ_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq generate failed: %s", exc)
    return ""


async def analyze_feedback_and_optimize():
    """
    Analysiert negatives Feedback der letzten 7 Tage,
    erkennt Muster und generiert verbesserte System-Prompts.
    Ergebnis wird als Vorschlag in DB gespeichert (Admin muss genehmigen).
    """
    db_path = os.getenv("DATABASE_PATH", "app.db")
    vorschläge_erstellt = 0

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            vor_7_tagen = (datetime.utcnow() - timedelta(days=7)).isoformat()

            # Negatives Feedback pro Fach gruppiert
            cursor = await db.execute(
                """SELECT fach, COUNT(*) as anzahl,
                       GROUP_CONCAT(frage, ' ||| ') as fragen,
                       GROUP_CONCAT(kommentar, ' ||| ') as kommentare
                FROM chat_feedbacks_v2
                WHERE bewertung = 'negativ'
                AND created_at >= ?
                AND fach != ''
                GROUP BY fach
                HAVING anzahl >= 3
                ORDER BY anzahl DESC""",
                (vor_7_tagen,)
            )
            fach_feedback = await cursor.fetchall()

            for row in fach_feedback:
                rd = dict(row)
                fach = rd.get("fach", "")
                anzahl = rd.get("anzahl", 0)
                fragen = rd.get("fragen", "")[:1500]
                kommentare = rd.get("kommentare", "")[:1000]

                # KI analysiert die Probleme
                analyse = await _groq_generate(
                    f"Du bist ein Prompt-Engineering-Experte.\n\n"
                    f"Hier sind {anzahl} negative Feedbacks im Fach {fach}:\n\n"
                    f"FRAGEN die schlecht beantwortet wurden:\n{fragen}\n\n"
                    f"KOMMENTARE der Schüler:\n{kommentare}\n\n"
                    f"1. Identifiziere die 3 häufigsten Probleme.\n"
                    f"2. Erstelle einen verbesserten System-Prompt "
                    f"der diese Probleme löst.\n\n"
                    f"Format:\n"
                    f"PROBLEME:\n- Problem 1\n- Problem 2\n- Problem 3\n\n"
                    f"NEUER SYSTEM-PROMPT:\n[der verbesserte Prompt]",
                    max_tokens=800,
                    temperature=0.3,
                )

                if not analyse:
                    continue

                # Probleme und Prompt extrahieren
                probleme = ""
                neuer_prompt = ""
                if "PROBLEME:" in analyse and "NEUER SYSTEM-PROMPT:" in analyse:
                    teile = analyse.split("NEUER SYSTEM-PROMPT:")
                    probleme = teile[0].replace("PROBLEME:", "").strip()
                    neuer_prompt = teile[1].strip() if len(teile) > 1 else ""
                else:
                    probleme = analyse[:300]
                    neuer_prompt = analyse

                # Vorschlag in DB speichern
                await db.execute(
                    """INSERT INTO prompt_vorschlaege
                    (fach, probleme, neuer_prompt, feedback_count, status)
                    VALUES (?, ?, ?, ?, 'ausstehend')""",
                    (fach, probleme[:500], neuer_prompt[:2000], anzahl),
                )
                vorschläge_erstellt += 1

            await db.commit()
            logger.info("Prompt-Optimierung: %d neue Vorschläge erstellt",
                        vorschläge_erstellt)

    except Exception as exc:
        logger.error("Prompt-Optimierung fehlgeschlagen: %s", exc)

    return vorschläge_erstellt


async def prompt_genehmigen(vorschlag_id: int) -> bool:
    """Admin genehmigt einen Prompt-Vorschlag → wird aktiv."""
    db_path = os.getenv("DATABASE_PATH", "app.db")
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                "SELECT * FROM prompt_vorschlaege WHERE id = ?",
                (vorschlag_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return False

            rd = dict(row)
            fach = rd.get("fach", "")
            neuer_prompt = rd.get("neuer_prompt", "")

            # Status updaten
            await db.execute(
                """UPDATE prompt_vorschlaege
                SET status = 'genehmigt', genehmigt_am = datetime('now')
                WHERE id = ?""",
                (vorschlag_id,)
            )
            await db.commit()

            # Prompt sofort aktivieren
            AKTIVE_PROMPTS[fach] = neuer_prompt
            logger.info("Prompt für %s genehmigt (ID: %d)", fach, vorschlag_id)
            return True

    except Exception as exc:
        logger.error("Prompt genehmigen fehlgeschlagen: %s", exc)
        return False


# Wöchentlicher Job (Montag 04:00)
async def weekly_prompt_optimization():
    """Läuft jeden Montag um 04:00 — analysiert Feedback und optimiert."""
    logger.info("Wöchentliche Prompt-Optimierung gestartet")
    count = await analyze_feedback_and_optimize()
    logger.info("Wöchentliche Prompt-Optimierung: %d Vorschläge", count)
    return count
