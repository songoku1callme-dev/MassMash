"""Erklärungs-System: Intelligente Erklärungen an jedem Punkt der App.

Feature 1: POST /api/erklaerung/schnell — Quick 2-3 sentence explanation
Feature 2: POST /api/erklaerung/stufenweise — Three-level explanation (ELI5/Normal/Fortgeschritten)
Feature 3: POST /api/quiz/erklaerung — Personalized quiz explanation
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.auth import get_current_user
from app.services.model_router import _groq_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/erklaerung", tags=["erklaerung"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ErklaerRequest(BaseModel):
    thema: str
    fach: Optional[str] = "Allgemein"
    kontext: Optional[str] = ""
    tiefe: Optional[str] = "normal"  # einfach | normal | ausfuehrlich


class StufenweiseRequest(BaseModel):
    thema: str
    fach: Optional[str] = "Allgemein"


class QuizErklaerungRequest(BaseModel):
    frage: str
    richtige_antwort: str
    schueler_antwort: str
    fach: Optional[str] = "Allgemein"
    war_richtig: bool = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Feature 1: Schnell-Erklärung (2-3 Sätze)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/schnell")
async def erklaerung_schnell(
    request: ErklaerRequest,
    current_user: dict = Depends(get_current_user),
):
    """Quick explanation: 2-3 sentences about any topic."""
    kontext_info = f"\nKontext: {request.kontext}" if request.kontext else ""

    prompt = (
        f"Erkläre kurz und verständlich für einen Schüler: {request.thema}\n"
        f"Fach: {request.fach}{kontext_info}\n\n"
        f"Antworte in 2-3 Sätzen auf Deutsch. Klar, präzise, schülerfreundlich."
    )

    result = await _groq_chat(
        "llama-3.3-70b-versatile",
        [
            {"role": "system", "content": "Du bist ein freundlicher Nachhilfelehrer. Erkläre kurz und verständlich."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=300,
    )

    if not result:
        result = f"Zum Thema '{request.thema}': Leider konnte keine Erklärung generiert werden. Versuche es im Chat für eine ausführliche Antwort."

    return {"erklaerung": result, "thema": request.thema, "fach": request.fach}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Feature 2: Stufenweise Erklärung (3 Level)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/stufenweise")
async def erklaerung_stufenweise(
    request: StufenweiseRequest,
    current_user: dict = Depends(get_current_user),
):
    """Three-level explanation: ELI5, Normal, Fortgeschritten."""
    prompt = (
        f"Erkläre das Thema '{request.thema}' (Fach: {request.fach}) auf DREI verschiedenen Niveaus.\n\n"
        f"Antworte EXAKT in diesem Format (ohne Markdown-Codeblöcke):\n"
        f"EINFACH: [Erklärung wie für ein 10-jähriges Kind, 2-3 Sätze, mit Alltagsbeispiel]\n"
        f"NORMAL: [Erklärung für einen Schüler Klasse 8-10, 3-4 Sätze, mit Fachbegriffen]\n"
        f"PROFI: [Erklärung für Oberstufe/Abitur, 4-5 Sätze, wissenschaftlich präzise]\n\n"
        f"Jede Stufe MUSS mit dem Keyword EINFACH:, NORMAL: oder PROFI: beginnen."
    )

    result = await _groq_chat(
        "llama-3.3-70b-versatile",
        [
            {"role": "system", "content": "Du bist ein erfahrener Pädagoge. Erkläre auf drei Niveaus."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=800,
    )

    # Parse the three levels from the response
    einfach = ""
    normal = ""
    profi = ""

    if result:
        lines = result.replace("\n\n", "\n").split("\n")
        current_level = ""
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.upper().startswith("EINFACH:"):
                current_level = "einfach"
                einfach = line_stripped[8:].strip()
            elif line_stripped.upper().startswith("NORMAL:"):
                current_level = "normal"
                normal = line_stripped[7:].strip()
            elif line_stripped.upper().startswith("PROFI:"):
                current_level = "profi"
                profi = line_stripped[6:].strip()
            elif current_level and line_stripped:
                if current_level == "einfach":
                    einfach += " " + line_stripped
                elif current_level == "normal":
                    normal += " " + line_stripped
                elif current_level == "profi":
                    profi += " " + line_stripped

    # Fallbacks if parsing failed
    if not einfach:
        einfach = f"{request.thema} ist ein wichtiges Thema. Stell dir vor, es funktioniert wie ein einfaches Beispiel aus dem Alltag."
    if not normal:
        normal = f"{request.thema} beschreibt einen Prozess, der in {request.fach} eine zentrale Rolle spielt."
    if not profi:
        profi = f"{request.thema} ist ein komplexes Konzept, das im Abitur relevant ist. Vertiefe es im Chat."

    return {
        "thema": request.thema,
        "fach": request.fach,
        "stufen": {
            "einfach": einfach,
            "normal": normal,
            "profi": profi,
        },
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Feature 3: Quiz-Erklärung (personalisiert)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/quiz")
async def quiz_erklaerung(
    request: QuizErklaerungRequest,
    current_user: dict = Depends(get_current_user),
):
    """Personalized quiz explanation based on whether answer was correct/incorrect."""
    if request.war_richtig:
        prompt = (
            f"Der Schüler hat die Frage RICHTIG beantwortet!\n"
            f"Frage: {request.frage}\n"
            f"Richtige Antwort: {request.richtige_antwort}\n"
            f"Fach: {request.fach}\n\n"
            f"Bestätige kurz (1 Satz) und gib dann einen interessanten Zusatzfakt zum Thema.\n"
            f"Format: Richtig! [Bestätigung]. Wusstest du: [interessanter Fakt]"
        )
    else:
        prompt = (
            f"Der Schüler hat die Frage FALSCH beantwortet.\n"
            f"Frage: {request.frage}\n"
            f"Schüler-Antwort: {request.schueler_antwort}\n"
            f"Richtige Antwort: {request.richtige_antwort}\n"
            f"Fach: {request.fach}\n\n"
            f"Erkläre:\n"
            f"1. Warum die Schüler-Antwort falsch ist (1 Satz)\n"
            f"2. Warum die richtige Antwort stimmt (1-2 Sätze)\n"
            f"3. Eine Eselsbrücke zum Merken (1 Satz)"
        )

    result = await _groq_chat(
        "llama-3.3-70b-versatile",
        [
            {"role": "system", "content": "Du bist ein einfühlsamer Nachhilfelehrer. Erkläre verständlich und ermutigend."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=400,
    )

    if not result:
        if request.war_richtig:
            result = f"Richtig! Die Antwort '{request.richtige_antwort}' ist korrekt."
        else:
            result = f"Die richtige Antwort ist: {request.richtige_antwort}. Versuche es beim nächsten Mal!"

    return {
        "erklaerung": result,
        "war_richtig": request.war_richtig,
        "frage": request.frage,
        "richtige_antwort": request.richtige_antwort,
    }
