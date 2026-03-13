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

# Vision-fähige Modelle (Groq) — mit Fallback-Kette
# NOTE: llama-3.2-*-vision-preview models are DECOMMISSIONED (as of 2026)
GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",      # Primär
    "meta-llama/llama-4-maverick-17b-128e-instruct",  # Fallback
]

# OpenAI GPT-4o Vision — Gemini-Level quality for complex math
OPENAI_VISION_MODELS = [
    "gpt-4o",           # Best quality for math/formulas
    "gpt-4o-mini",      # Cheaper fallback
]

BILD_ANALYSE_PROMPT = """Du bist LUMNOS, ein KI-Lerncoach für deutsche Schüler (Gemini-Level Vision).
Analysiere dieses Bild VOLLSTÄNDIG und GRÜNDLICH mit höchster mathematischer Präzision.

Führe IMMER diese Schritte durch:

**SCHRITT 1 — BILD-ERKENNUNG & TRANSKRIPTION:**
Beschreibe ALLES was du siehst:
- Texte: Transkribiere WÖRTLICH
- Formeln: Schreibe sie EXAKT in LaTeX ($...$)
- Diagramme: Beschreibe Achsen, Werte, Kurvenverläufe
- Tabellen: Reproduziere als Markdown-Tabelle
- Koordinatensysteme: Lies ALLE Werte, Punkte, Geraden ab
- Geometrie: Erkenne Winkel, Längen, Formen

**SCHRITT 2 — AUFGABEN ERKENNEN:**
Falls Aufgaben/Fragen auf dem Bild sind:
- Zähle wie viele Aufgaben es gibt
- Benenne jede Aufgabe (Aufgabe 1, Aufgabe 2, etc.)
- Erkläre was jede Aufgabe verlangt

**SCHRITT 3 — VOLLSTÄNDIGER LÖSUNGSWEG:**
Löse JEDE erkannte Aufgabe mit KOMPLETTEM Lösungsweg:

Bei **Mathematik**:
- Schreibe JEDEN Schritt einzeln auf
- Verwende LaTeX für alle Formeln: $f(x) = ax^2 + bx + c$
- Zeige Umformungen Schritt für Schritt
- Bei Gleichungen: Löse vollständig mit Probe
- Bei Ableitungen: Zeige jede Regel (Ketten-, Produkt-, Quotientenregel)
- Bei Integralen: Zeige Stammfunktion + Grenzen einsetzen
- Bei Geometrie: Zeichne Skizze in Worten, berechne mit Formeln
- Bei Stochastik: Baumdiagramm, Pfadregeln, Ergebnis

Bei **Physik/Chemie**:
- Gegebene Größen aufschreiben mit Einheiten
- Formel angeben, umstellen, einsetzen
- Ergebnis mit korrekter Einheit

Bei **Textaufgaben**: Vollständige, strukturierte Antwort
Bei **Diagrammen**: Interpretation aller Datenpunkte

**SCHRITT 4 — ERGEBNIS-CHECK:**
- Überprüfe dein Ergebnis (Probe, Plausibilität)
- Markiere das Endergebnis deutlich: **Ergebnis: ...**

**SCHRITT 5 — LERN-TIPP:**
Gib einen Tipp, wie der Schüler ähnliche Aufgaben lösen kann.
Nenne die verwendete Methode/Formel beim Namen.

WICHTIG:
- Antworte IMMER auf Deutsch
- NIEMALS "Ich kann das Bild nicht sehen" sagen — analysiere IMMER
- Antworte NIEMALS mit internen Tags wie <think>, <thinking>, <output>
- Bei Mathe: JEDER Rechenschritt muss sichtbar sein
- Formeln IMMER in LaTeX: $...$ (inline) oder $$...$$ (Block)
"""


def _get_groq_key() -> str:
    return os.getenv("GROQ_API_KEY", "")


def _get_openai_key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


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
    openai_key = _get_openai_key()

    if not groq_key and not openai_key:
        raise HTTPException(status_code=500, detail="Weder GROQ_API_KEY noch OPENAI_API_KEY konfiguriert")

    # Vision API aufrufen: Groq (schnell) -> OpenAI GPT-4o (Gemini-Level Qualitaet)
    logger.info("[VISION] Start — Datei: %s, Groesse: %d bytes, MIME: %s", file.filename, len(bild_bytes), content_type)
    last_error = ""

    # Phase 1: Groq Vision (schnell + kostenlos)
    if groq_key:
        for model in GROQ_VISION_MODELS:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
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
                            "max_tokens": 4000,
                            "temperature": 0.1,
                        },
                    )

                    logger.info("[VISION] Groq Model: %s, Status: %d", model, response.status_code)

                    if response.status_code == 200:
                        data = response.json()
                        usage = data.get("usage", {})
                        if usage:
                            track_tokens(
                                usage.get("prompt_tokens", 0),
                                usage.get("completion_tokens", 0),
                            )
                        analyse = data["choices"][0]["message"]["content"]
                        analyse = _clean_vision_response(analyse)
                        logger.info("[VISION] Erfolg mit %s — %d Zeichen", model, len(analyse))
                        return {
                            "analyse": analyse,
                            "model": model,
                            "dateiname": file.filename,
                            "fach": fach,
                        }
                    else:
                        error_detail = response.text[:300]
                        logger.warning("[VISION] %d auf %s: %s", response.status_code, model, error_detail)
                        last_error = f"{response.status_code}: {error_detail}"
                        continue

            except Exception as e:
                logger.error("[VISION ERROR] %s: %s: %s", model, type(e).__name__, e)
                last_error = f"{type(e).__name__}: {e}"
                continue

    # Phase 2: OpenAI GPT-4o Vision (Gemini-Level — beste Qualitaet fuer Mathe)
    if openai_key:
        logger.info("[VISION] Groq fehlgeschlagen, versuche OpenAI GPT-4o Vision...")
        for model in OPENAI_VISION_MODELS:
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {openai_key}",
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
                                            "detail": "high",
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": user_prompt,
                                    },
                                ],
                            }],
                            "max_tokens": 4000,
                            "temperature": 0.1,
                        },
                    )

                    logger.info("[VISION] OpenAI Model: %s, Status: %d", model, response.status_code)

                    if response.status_code == 200:
                        data = response.json()
                        usage = data.get("usage", {})
                        if usage:
                            track_tokens(
                                usage.get("prompt_tokens", 0),
                                usage.get("completion_tokens", 0),
                            )
                        analyse = data["choices"][0]["message"]["content"]
                        analyse = _clean_vision_response(analyse)
                        logger.info("[VISION] Erfolg mit OpenAI %s — %d Zeichen", model, len(analyse))
                        return {
                            "analyse": analyse,
                            "model": f"openai/{model}",
                            "dateiname": file.filename,
                            "fach": fach,
                        }
                    else:
                        error_detail = response.text[:300]
                        logger.warning("[VISION] OpenAI %d auf %s: %s", response.status_code, model, error_detail)
                        last_error = f"OpenAI {response.status_code}: {error_detail}"
                        continue

            except Exception as e:
                logger.error("[VISION ERROR] OpenAI %s: %s: %s", model, type(e).__name__, e)
                last_error = f"OpenAI {type(e).__name__}: {e}"
                continue

    logger.error("[VISION] Alle Modelle fehlgeschlagen. Letzter Fehler: %s", last_error)
    raise HTTPException(
        status_code=503,
        detail=f"Bild konnte nicht analysiert werden. Fehler: {last_error[:200]}",
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
    openai_key = _get_openai_key()

    if not groq_key and not openai_key:
        raise HTTPException(status_code=500, detail="Weder GROQ_API_KEY noch OPENAI_API_KEY konfiguriert")

    async def generate():
        # Phase 1: Groq Vision (schnell)
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
                        logger.info("[VISION STREAM] Model: %s, Status: %d", model, resp.status_code)
                        if resp.status_code == 429:
                            logger.warning("[VISION STREAM] 429 Rate Limit auf %s", model)
                            continue
                        if resp.status_code != 200:
                            logger.error("[VISION STREAM] %d Error auf %s", resp.status_code, model)
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

        # Phase 2: OpenAI GPT-4o Vision fallback (Gemini-Level)
        if openai_key:
            logger.info("[VISION STREAM] Groq fehlgeschlagen, versuche OpenAI...")
            for model in OPENAI_VISION_MODELS:
                try:
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        async with client.stream(
                            "POST",
                            "https://api.openai.com/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {openai_key}",
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
                                                "detail": "high",
                                            },
                                        },
                                        {"type": "text", "text": user_prompt},
                                    ],
                                }],
                                "max_tokens": 4000,
                                "temperature": 0.1,
                            },
                        ) as resp:
                            logger.info("[VISION STREAM] OpenAI %s, Status: %d", model, resp.status_code)
                            if resp.status_code != 200:
                                continue

                            async for line in resp.aiter_lines():
                                if not line.startswith("data: "):
                                    continue
                                payload = line[6:]
                                if payload.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(payload)
                                    usage = chunk.get("usage", {})
                                    if usage:
                                        track_tokens(
                                            usage.get("prompt_tokens", 0),
                                            usage.get("completion_tokens", 0),
                                        )
                                    delta = chunk["choices"][0].get("delta", {})
                                    text = delta.get("content", "")
                                    if text:
                                        yield f"data: {json.dumps({'content': text})}\n\n"
                                except Exception:
                                    continue

                            yield f"data: {json.dumps({'done': True, 'model': f'openai/{model}'})}\n\n"
                            return  # Success
                except Exception as e:
                    logger.error("[STREAM ERROR] OpenAI Vision %s: %s", model, e)
                    continue

        yield f"data: {json.dumps({'error': 'Analyse fehlgeschlagen'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
