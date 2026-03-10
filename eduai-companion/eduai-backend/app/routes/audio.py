"""Audio routes — Whisper transcription + KI analysis via Groq.

Transcribes audio files using Groq's Whisper Large v3,
then passes the transcription to the LLM for analysis and answering.
"""
import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException

from app.core.auth import get_current_user
from app.services.ai_engine import track_tokens
from app.services.model_router import _groq_chat, MODELL_REIHENFOLGE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])

ERLAUBTE_AUDIO_FORMATE = [
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/wave", "audio/x-wav",
    "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/aac",
    "audio/ogg", "audio/vorbis", "audio/opus",
    "audio/webm", "audio/flac", "audio/x-flac",
    "video/webm", "video/mp4",
    "application/octet-stream",  # Fallback für unbekannte MIME-Types
]

ERLAUBTE_AUDIO_ENDUNGEN = {
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".aac", ".opus", ".wma",
}

MAX_AUDIO_MB = 25  # Groq Whisper limit


def _get_groq_key() -> str:
    return os.getenv("GROQ_API_KEY", "")


def _clean_ai_response(text: str) -> str:
    """Strip internal LLM tags from response."""
    import re
    if not text:
        return ""
    text = re.sub(r'<output>(.*?)</output>', r'\1', text, flags=re.DOTALL)
    text = text.replace('<output>', '').replace('</output>', '')
    for tag in ('thinking', 'think', 'reasoning', 'internal', 'scratchpad'):
        text = re.sub(rf'<{tag}>.*?</{tag}>', '', text, flags=re.DOTALL)
        text = re.sub(rf'<{tag}>.*', '', text, flags=re.DOTALL)
        text = text.replace(f'</{tag}>', '').replace(f'<{tag}>', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


@router.post("/transkribieren")
async def audio_transkribieren(
    file: UploadFile = File(...),
    frage: Optional[str] = Form(None),
    fach: Optional[str] = Form("Allgemein"),
    sprache: Optional[str] = Form("de"),
    _user: dict = Depends(get_current_user),
):
    """Transkribiert eine Audiodatei mit Whisper via Groq.

    Optional: Beantwortet eine Frage basierend auf dem transkribierten Inhalt.
    """
    # Größe prüfen
    audio_bytes = await file.read()
    size_mb = len(audio_bytes) / (1024 * 1024)

    if size_mb > MAX_AUDIO_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß ({size_mb:.1f}MB). Maximum: {MAX_AUDIO_MB}MB",
        )

    content_type = file.content_type or "audio/mpeg"
    # Prüfe MIME-Type ODER Dateiendung (robuster)
    dateiname = (file.filename or "").lower()
    endung = "." + dateiname.rsplit(".", 1)[-1] if "." in dateiname else ""
    mime_ok = content_type in ERLAUBTE_AUDIO_FORMATE or content_type.startswith("audio/")
    endung_ok = endung in ERLAUBTE_AUDIO_ENDUNGEN
    if not mime_ok and not endung_ok:
        logger.warning("[AUDIO] Abgelehnt: MIME=%s, Datei=%s", content_type, dateiname)
        raise HTTPException(
            status_code=400,
            detail=f"Format nicht unterstützt (MIME: {content_type}). Erlaubt: MP3, WAV, M4A, OGG, FLAC, WebM",
        )
    logger.info("[AUDIO] Akzeptiert: MIME=%s, Datei=%s, Größe=%.1fMB", content_type, dateiname, size_mb)

    groq_key = _get_groq_key()
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY nicht konfiguriert")

    # Schritt 1: Audio transkribieren via Groq Whisper
    transkription = ""
    dauer = 0.0
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                },
                files={
                    "file": (file.filename, audio_bytes, content_type),
                },
                data={
                    "model": "whisper-large-v3",
                    "language": sprache or "de",
                    "response_format": "verbose_json",
                },
            )

            if response.status_code != 200:
                error_text = response.text[:200]
                logger.error("Whisper transcription failed: %d — %s", response.status_code, error_text)
                raise HTTPException(
                    status_code=502,
                    detail=f"Transkription fehlgeschlagen: {error_text}",
                )

            transkription_data = response.json()
            transkription = transkription_data.get("text", "")
            dauer = transkription_data.get("duration", 0)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Whisper error: %s", e)
        raise HTTPException(status_code=502, detail=f"Audio-Fehler: {str(e)[:100]}")

    if not transkription:
        return {
            "transkription": "",
            "dauer_sekunden": 0,
            "ki_antwort": "Keine Sprache erkannt. Ist die Datei eine Audiodatei mit Sprache?",
            "dateiname": file.filename,
            "fach": fach,
            "model_used": "whisper-large-v3",
        }

    # Schritt 2: KI antwortet auf Transkription
    ki_prompt = f"""Du bist LUMNOS, ein KI-Lerncoach für deutsche Schüler.

Ein Schüler hat eine Audiodatei hochgeladen mit diesem Inhalt:
"{transkription}"

Fach-Kontext: {fach}
"""
    if frage:
        ki_prompt += f"\nDer Schüler stellt diese Frage dazu:\n{frage}"
        ki_prompt += "\n\nBeantworte die Frage vollständig und präzise."
    else:
        ki_prompt += """
Analysiere den Audio-Inhalt:
1. Fasse zusammen was gesagt wurde
2. Falls Aufgaben oder Fragen erwähnt werden: Löse sie vollständig
3. Falls Vokabular/Fakten genannt werden: Erkläre sie
4. Gib einen Lern-Tipp basierend auf dem Inhalt

Antworte IMMER auf Deutsch. Nutze LaTeX ($...$) für Formeln.
Antworte NIEMALS mit internen Tags wie <think>, <thinking>, <output>.
"""

    # Use the model router's _groq_chat with fallback
    messages = [
        {"role": "system", "content": "Du bist LUMNOS, ein KI-Lerncoach. Antworte auf Deutsch. Nutze LaTeX für Formeln."},
        {"role": "user", "content": ki_prompt},
    ]
    model_used = "llama-3.3-70b-versatile"
    ki_antwort = await _groq_chat(model_used, messages, temperature=0.3, max_tokens=1500)
    ki_antwort = _clean_ai_response(ki_antwort)

    return {
        "transkription": transkription,
        "dauer_sekunden": round(dauer, 1),
        "ki_antwort": ki_antwort or "Analyse konnte nicht durchgeführt werden.",
        "dateiname": file.filename,
        "fach": fach,
        "model_used": model_used,
    }


@router.post("/sprache-erkennen")
async def sprache_erkennen(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
):
    """Erkennt nur die Sprache einer Audiodatei (ohne KI-Analyse)."""
    audio_bytes = await file.read()
    groq_key = _get_groq_key()
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY nicht konfiguriert")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {groq_key}"},
                files={"file": (file.filename, audio_bytes, file.content_type or "audio/mpeg")},
                data={"model": "whisper-large-v3", "response_format": "verbose_json"},
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "sprache": data.get("language", "unbekannt"),
                    "text_vorschau": data.get("text", "")[:100],
                }
            return {"error": f"Spracherkennung fehlgeschlagen: HTTP {response.status_code}"}
    except Exception as e:
        return {"error": f"Spracherkennung fehlgeschlagen: {str(e)[:100]}"}
