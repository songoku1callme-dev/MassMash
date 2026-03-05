"""Vision routes — AI-powered image analysis via Groq Vision API.

Supports full image analysis: text recognition, task solving, diagram interpretation.
Uses Llama 4 Vision models with automatic fallback.
"""
import base64
import json
import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from app.core.auth import get_current_user
from app.services.ai_engine import track_tokens

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vision", tags=["vision"])

# Vision-fähige Modelle (Groq)
GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",    # Primär
    "meta-llama/llama-4-maverick-17b-128e-instruct",  # Fallback
]

BILD_ANALYSE_PROMPT = """Du bist LUMNOS, ein KI-Lerncoach für deutsche Schüler.
Analysiere dieses Bild VOLLSTÄNDIG und GRÜNDLICH.

Führe IMMER diese Schritte durch:

**SCHRITT 1 — BILD-BESCHREIBUNG:**
Beschreibe was du auf dem Bild siehst (Texte, Objekte, Diagramme,
Tabellen, Formeln, Personen, Szenen — alles).

**SCHRITT 2 — AUFGABEN ERKENNEN:**
Falls Aufgaben/Fragen auf dem Bild sind:
- Zähle wie viele Aufgaben es gibt
- Benenne jede Aufgabe (Aufgabe 1, Aufgabe 2, etc.)
- Erkläre was jede Aufgabe verlangt

**SCHRITT 3 — AUFGABEN LÖSEN:**
Löse JEDE erkannte Aufgabe vollständig:
- Bei Mathe: Vollständiger Rechenweg mit LaTeX ($...$)
- Bei Textaufgaben: Vollständige Antwort
- Bei Bildbeschreibungs-Aufgaben: Detaillierte Beschreibung
- Bei Diagrammen: Interpretation aller Daten
- Bei Chemie/Physik: Formeln und Einheiten korrekt

**SCHRITT 4 — LERN-TIPP:**
Gib einen kurzen Tipp was der Schüler aus dieser Aufgabe
lernen kann oder wie er ähnliche Aufgaben lösen kann.

WICHTIG:
- Antworte IMMER auf Deutsch
- Wenn Text auf dem Bild ist: Transkribiere ihn WÖRTLICH
- Wenn Formeln sichtbar sind: Schreibe sie in LaTeX
- Wenn ein Koordinatensystem sichtbar ist: Lies alle Werte ab
- Wenn eine Tabelle sichtbar ist: Reproduziere sie als Markdown
- NIEMALS "Ich kann das Bild nicht sehen" sagen — analysiere immer
- Antworte NIEMALS mit internen Tags wie <think>, <thinking>, <output>
"""


def _get_groq_key() -> str:
    return os.getenv("GROQ_API_KEY", "")


def _clean_vision_response(text: str) -> str:
    """Strip internal LLM tags from vision response."""
    import re
    if not text:
        return ""
    # Remove <output> wrapper
    text = re.sub(r'<output>(.*?)</output>', r'\1', text, flags=re.DOTALL)
    text = text.replace('<output>', '').replace('</output>', '')
    # Remove thinking tags
    for tag in ('thinking', 'think', 'reasoning', 'internal', 'scratchpad'):
        text = re.sub(rf'<{tag}>.*?</{tag}>', '', text, flags=re.DOTALL)
        text = re.sub(rf'<{tag}>.*', '', text, flags=re.DOTALL)
        text = text.replace(f'</{tag}>', '').replace(f'<{tag}>', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


@router.post("/analyse")
async def analyse_bild(
    file: UploadFile = File(...),
    frage: Optional[str] = Form(None),
    fach: Optional[str] = Form("Allgemein"),
    _user: dict = Depends(get_current_user),
):
    """Analysiert ein Bild vollständig mit Groq Vision API.

    Optional: Zusätzliche Frage zum Bild und Fach-Kontext.
    """
    # Bild einlesen und zu Base64 konvertieren
    bild_bytes = await file.read()
    if len(bild_bytes) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(status_code=400, detail="Bild zu groß. Maximum: 10MB")

    bild_b64 = base64.b64encode(bild_bytes).decode("utf-8")

    # MIME-Type erkennen
    content_type = file.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Nur Bilddateien erlaubt (JPG, PNG, GIF, WebP)",
        )

    # Prompt bauen
    user_prompt = BILD_ANALYSE_PROMPT
    if frage:
        user_prompt += f"\n\nZUSÄTZLICHE FRAGE DES SCHÜLERS:\n{frage}"
    if fach and fach != "Allgemein":
        user_prompt += f"\n\nFACH-KONTEXT: {fach}"

    groq_key = _get_groq_key()
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY nicht konfiguriert")

    # Groq Vision API aufrufen (mit Fallback)
    for model in GROQ_VISION_MODELS:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{content_type};base64,{bild_b64}",
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": user_prompt,
                                },
                            ],
                        }],
                        "max_tokens": 2000,
                        "temperature": 0.1,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    # Track tokens
                    usage = data.get("usage", {})
                    if usage:
                        track_tokens(
                            usage.get("prompt_tokens", 0),
                            usage.get("completion_tokens", 0),
                        )
                    analyse = data["choices"][0]["message"]["content"]
                    analyse = _clean_vision_response(analyse)

                    return {
                        "analyse": analyse,
                        "model": model,
                        "dateiname": file.filename,
                        "fach": fach,
                    }
                elif response.status_code == 429:
                    logger.warning("[RATE LIMIT] Vision %s → nächstes Modell...", model)
                    continue
                else:
                    error_detail = response.text[:200]
                    logger.error("[ERROR] Vision %s: %d — %s", model, response.status_code, error_detail)
                    continue

        except Exception as e:
            logger.error("[ERROR] Vision %s: %s", model, e)
            continue

    raise HTTPException(
        status_code=503,
        detail="Bild konnte nicht analysiert werden. Bitte versuche es erneut.",
    )


@router.post("/analyse-stream")
async def analyse_bild_stream(
    file: UploadFile = File(...),
    frage: Optional[str] = Form(None),
    fach: Optional[str] = Form("Allgemein"),
    _user: dict = Depends(get_current_user),
):
    """Streaming-Version der Bild-Analyse für Live-Anzeige."""
    bild_bytes = await file.read()
    if len(bild_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bild zu groß. Maximum: 10MB")

    bild_b64 = base64.b64encode(bild_bytes).decode("utf-8")
    content_type = file.content_type or "image/jpeg"

    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Nur Bilddateien erlaubt")

    user_prompt = BILD_ANALYSE_PROMPT
    if frage:
        user_prompt += f"\n\nZUSÄTZLICHE FRAGE: {frage}"
    if fach and fach != "Allgemein":
        user_prompt += f"\n\nFACH: {fach}"

    groq_key = _get_groq_key()
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY nicht konfiguriert")

    async def generate():
        for model in GROQ_VISION_MODELS:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {groq_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "stream": True,
                            "messages": [{
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{content_type};base64,{bild_b64}",
                                        },
                                    },
                                    {"type": "text", "text": user_prompt},
                                ],
                            }],
                            "max_tokens": 2000,
                            "temperature": 0.1,
                        },
                    ) as resp:
                        if resp.status_code == 429:
                            logger.warning("[RATE LIMIT] Vision stream %s → nächstes Modell", model)
                            continue
                        if resp.status_code != 200:
                            logger.error("Vision stream %s HTTP %d", model, resp.status_code)
                            continue

                        total_chars = 0
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            payload = line[6:]
                            if payload.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(payload)
                                # Track usage from final chunk
                                usage = (
                                    chunk.get("x_groq", {}).get("usage", {})
                                    or chunk.get("usage", {})
                                )
                                if usage:
                                    track_tokens(
                                        usage.get("prompt_tokens", 0),
                                        usage.get("completion_tokens", 0),
                                    )
                                delta = chunk["choices"][0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    total_chars += len(text)
                                    yield f"data: {json.dumps({'content': text})}\n\n"
                            except Exception:
                                continue

                        # Done event
                        yield f"data: {json.dumps({'done': True, 'model': model})}\n\n"
                        return  # Success
            except Exception as e:
                logger.error("[STREAM ERROR] Vision %s: %s", model, e)
                continue

        yield f"data: {json.dumps({'error': 'Analyse fehlgeschlagen'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
