"""Schulbuch-Scanner: OCR -> Quiz + Karteikarten (Pro/Max Feature).

LUMNOS Fächer-Expansion 5.0 Block 5:
- Image upload with OCR text extraction
- KI-powered analysis (Hauptthema, Lernziele, Schlüsselbegriffe)
- Auto-generate quiz questions from scanned text
- Auto-generate flashcards from key terms
- Tier-gated: Pro/Max only (revenue feature)
"""
import json
import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schulbuch", tags=["schulbuch"])


def _ocr_extract_text(image_bytes: bytes) -> str:
    """Extract text from image using pytesseract (German language)."""
    try:
        import pytesseract
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang="deu")
        return text.strip()
    except ImportError:
        # pytesseract not installed — use basic fallback
        logger.warning("pytesseract not installed, using OCR fallback")
        return ""
    except Exception as e:
        logger.error("OCR failed: %s", e)
        return ""


async def _groq_analyze(text: str, fach: str, groq_key: str) -> dict:
    """Use Groq to analyze scanned textbook text."""
    try:
        from groq import Groq

        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein Schulbuch-Analytiker. Analysiere den Text und extrahiere "
                        "strukturierte Informationen. Antworte NUR mit validem JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""Analysiere diesen Schulbuch-Text ({fach}):
"{text[:3000]}"

Extrahiere:
1. HAUPTTHEMA: Was wird erklärt? (1 Satz)
2. LERNZIELE: Was soll der Schüler lernen? (3-5 Punkte als Array)
3. SCHLUESSELBEGRIFFE: Wichtigste Fachbegriffe (max 10, als Array)
4. SCHWIERIGKEITSGRAD: leicht/mittel/schwer
5. KLASSE: Für welche Klasse ist das? (Schätzung als Zahl)

FORMAT: JSON mit keys: hauptthema, lernziele, schluesselbegriffe, schwierigkeitsgrad, klasse""",
                },
            ],
            max_tokens=800,
            temperature=0.3,
        )
        content = resp.choices[0].message.content or "{}"
        # Try to parse JSON from response
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error("Groq analyze failed: %s", e)
        return {
            "hauptthema": f"Schulbuch-Text ({fach})",
            "lernziele": ["Grundlagen verstehen", "Fachbegriffe lernen"],
            "schluesselbegriffe": [],
            "schwierigkeitsgrad": "mittel",
            "klasse": 10,
        }


async def _groq_generate_quiz(text: str, fach: str, difficulty: str, groq_key: str) -> list:
    """Generate quiz questions from scanned text using Groq."""
    try:
        from groq import Groq

        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein Quiz-Generator. Erstelle Quizfragen DIREKT aus dem gegebenen Text. "
                        "Antworte NUR mit einem JSON Array."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""Erstelle 10 Quizfragen DIREKT aus diesem Schulbuch-Text:
"{text[:3000]}"

WICHTIG: Fragen sollen NUR aus dem gescannten Text beantwortet werden können!
Kein Allgemeinwissen - nur was im Buch steht.
Fach: {fach}
Schwierigkeit: {difficulty}

FORMAT: JSON Array mit Objekten: question, options (4 Strings), correct_answer, explanation""",
                },
            ],
            max_tokens=2000,
            temperature=0.5,
        )
        content = resp.choices[0].message.content or "[]"
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error("Groq quiz generation failed: %s", e)
        return []


async def _groq_generate_flashcards(begriffe: list, fach: str, groq_key: str) -> list:
    """Generate flashcards from key terms using Groq."""
    if not begriffe:
        return []
    try:
        from groq import Groq

        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein Karteikarten-Generator. Erstelle Karteikarten für Fachbegriffe. "
                        "Antworte NUR mit einem JSON Array."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""Erstelle Karteikarten für diese Schlüsselbegriffe aus dem Schulbuch:
{json.dumps(begriffe, ensure_ascii=False)}

Fach: {fach}
Vorderseite: Begriff
Rückseite: Kurzdefinition (max 2 Sätze, aus dem Buch-Kontext)

FORMAT: JSON Array: [{{"vorne": "Begriff", "hinten": "Definition"}}]""",
                },
            ],
            max_tokens=1000,
            temperature=0.3,
        )
        content = resp.choices[0].message.content or "[]"
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error("Groq flashcard generation failed: %s", e)
        return [{"vorne": b, "hinten": f"Definition von {b}"} for b in begriffe[:10]]


@router.post("/scan")
async def scan_schulbuch(
    image: UploadFile = File(...),
    fach: str = Form("Allgemein"),
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Scan a textbook page: OCR -> Analyse -> Quiz + Karteikarten.

    Pro/Max feature only. Free users get a 403.
    """
    user_id = current_user["id"]

    # Check subscription tier
    cursor = await db.execute(
        "SELECT subscription_tier FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    tier = (dict(row).get("subscription_tier", "free") or "free") if row else "free"

    if tier == "free":
        raise HTTPException(
            status_code=403,
            detail="Schulbuch-Scanner ist ein Pro/Max Feature. Upgrade dein Abo!",
        )

    # Validate file
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Nur Bilddateien erlaubt (JPEG, PNG)")

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Datei zu gross (max. 10 MB)")

    # STEP 1: OCR - extract text from image
    ocr_text = _ocr_extract_text(image_bytes)

    if not ocr_text or len(ocr_text) < 20:
        # If OCR fails or too little text, try the existing OCR solver
        try:
            from app.services.ocr_solver import MathSolver

            ocr_text = MathSolver.ocr_image(image_bytes)
        except Exception:
            pass

    if not ocr_text or len(ocr_text) < 20:
        raise HTTPException(
            status_code=422,
            detail="Kein Text erkannt. Bitte ein deutlicheres Foto machen.",
        )

    groq_key = os.getenv("GROQ_API_KEY", "")

    # STEP 2: KI analyzes the textbook text
    analyse = await _groq_analyze(ocr_text, fach, groq_key)

    # STEP 3: Generate quiz from textbook content
    quiz = await _groq_generate_quiz(
        ocr_text, fach, analyse.get("schwierigkeitsgrad", "mittel"), groq_key
    )

    # STEP 4: Generate flashcards from key terms
    karteikarten = await _groq_generate_flashcards(
        analyse.get("schluesselbegriffe", []), fach, groq_key
    )

    # Save scan to DB
    scan_id = f"scan_{user_id}_{uuid.uuid4().hex[:8]}"
    try:
        await db.execute(
            """INSERT INTO schulbuch_scans
            (scan_id, user_id, fach, ocr_text, analyse, quiz, karteikarten, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                scan_id,
                user_id,
                fach,
                ocr_text,
                json.dumps(analyse, ensure_ascii=False),
                json.dumps(quiz, ensure_ascii=False),
                json.dumps(karteikarten, ensure_ascii=False),
            ),
        )
        await db.commit()
    except Exception as e:
        logger.warning("Could not save scan to DB: %s", e)

    return {
        "scan_id": scan_id,
        "thema": analyse.get("hauptthema", f"Schulbuch-Seite ({fach})"),
        "lernziele": analyse.get("lernziele", []),
        "schluesselbegriffe": analyse.get("schluesselbegriffe", []),
        "schwierigkeitsgrad": analyse.get("schwierigkeitsgrad", "mittel"),
        "klasse": analyse.get("klasse", 10),
        "quiz_fragen": len(quiz),
        "karteikarten": len(karteikarten),
        "preview": quiz[:3],
        "karteikarten_preview": karteikarten[:3],
    }


@router.get("/scans")
async def list_scans(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all scans for current user."""
    cursor = await db.execute(
        """SELECT scan_id, fach, analyse, created_at
        FROM schulbuch_scans WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 50""",
        (current_user["id"],),
    )
    rows = await cursor.fetchall()
    scans = []
    for r in rows:
        rd = dict(r)
        try:
            analyse = json.loads(rd.get("analyse", "{}"))
        except Exception:
            analyse = {}
        scans.append({
            "scan_id": rd["scan_id"],
            "fach": rd["fach"],
            "thema": analyse.get("hauptthema", ""),
            "created_at": rd["created_at"],
        })
    return {"scans": scans}


@router.get("/scan/{scan_id}")
async def get_scan(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get full scan details including quiz and flashcards."""
    cursor = await db.execute(
        "SELECT * FROM schulbuch_scans WHERE scan_id = ? AND user_id = ?",
        (scan_id, current_user["id"]),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Scan nicht gefunden")

    rd = dict(row)
    try:
        analyse = json.loads(rd.get("analyse", "{}"))
        quiz = json.loads(rd.get("quiz", "[]"))
        karteikarten = json.loads(rd.get("karteikarten", "[]"))
    except Exception:
        analyse, quiz, karteikarten = {}, [], []

    return {
        "scan_id": rd["scan_id"],
        "fach": rd["fach"],
        "ocr_text": rd.get("ocr_text", ""),
        "analyse": analyse,
        "quiz": quiz,
        "karteikarten": karteikarten,
        "created_at": rd.get("created_at", ""),
    }
