"""Voice Mode routes - Whisper STT + gTTS TTS.

Supreme 10.0 Phase 3: Voice chat with KI tutor.
"""
import io
import os
import logging
import tempfile
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.tier_guard import require_tier


class TTSRequest(BaseModel):
    text: str = ""
    lang: str = "de"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    _tier: None = Depends(require_tier("pro")),
):
    """Transcribe audio to text using Groq Whisper API."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise HTTPException(status_code=503, detail="Voice-Modus nicht verfügbar (kein API Key)")

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)

        audio_bytes = await audio.read()

        # Save to temp file for Groq API
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=(audio.filename or "audio.webm", f.read(), audio.content_type or "audio/webm"),
                language="de",
                prompt="Schüler fragt Lehrer auf Deutsch. Fachbegriffe: Mathematik, Physik, Chemie, Biologie, Deutsch, Geschichte.",
            )

        os.unlink(tmp_path)
        return {"text": transcript.text, "language": "de"}
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Transkription fehlgeschlagen: {str(e)}")


@router.post("/tts")
async def text_to_speech(
    text: Optional[str] = Query(None),
    lang: str = Query("de"),
    body: Optional[TTSRequest] = None,
    current_user: dict = Depends(get_current_user),
    _tier: None = Depends(require_tier("pro")),
):
    """Convert text to speech using gTTS. Accepts both query params and JSON body."""
    tts_text = text or (body.text if body else None)
    tts_lang = lang or (body.lang if body else "de") or "de"
    if not tts_text or len(tts_text) > 5000:
        raise HTTPException(status_code=400, detail="Text muss zwischen 1 und 5000 Zeichen sein")

    try:
        from gtts import gTTS

        tts = gTTS(text=tts_text, lang=tts_lang, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        return StreamingResponse(
            audio_buffer,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=response.mp3"},
        )
    except Exception as e:
        logger.error("TTS failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Sprachausgabe fehlgeschlagen: {str(e)}")


@router.post("/chat")
async def voice_chat(
    audio: UploadFile = File(...),
    session_id: int = 0,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    _tier: None = Depends(require_tier("pro")),
):
    """Full voice chat: transcribe -> AI respond -> TTS.

    Returns audio response directly.
    """
    # Step 1: Transcribe
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise HTTPException(status_code=503, detail="Voice-Modus nicht verfügbar")

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)

        audio_bytes = await audio.read()
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=(audio.filename or "audio.webm", f.read(), audio.content_type or "audio/webm"),
                language="de",
            )
        os.unlink(tmp_path)
        user_text = transcript.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transkription fehlgeschlagen: {str(e)}")

    # Step 2: Get AI response
    try:
        from app.services.groq_llm import call_groq_llm

        system_prompt = (
            "Du bist Lumnos, ein freundlicher KI-Tutor für deutsche Schüler. "
            "Antworte kurz und prägnant (max 3 Sätze), da deine Antwort vorgelesen wird. "
            "Verwende einfache Sprache, keine LaTeX-Formeln. "
            "Sei motivierend und ermutigend."
        )

        ai_response = call_groq_llm(
            prompt=user_text,
            system_prompt=system_prompt,
            subject="general",
            level="intermediate",
            language="de",
        )
    except Exception as e:
        ai_response = f"Entschuldigung, ich konnte deine Frage nicht verarbeiten: {str(e)}"

    # Step 3: TTS
    try:
        from gtts import gTTS

        tts = gTTS(text=ai_response, lang="de", slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        return StreamingResponse(
            audio_buffer,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=response.mp3",
                "X-Transcript": user_text,
                "X-Response": ai_response,
            },
        )
    except Exception as e:
        return {"transcript": user_text, "response": ai_response, "audio_error": str(e)}
