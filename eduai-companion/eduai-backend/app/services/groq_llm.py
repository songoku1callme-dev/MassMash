"""Groq LLM integration for Lumnos Companion.

Provides a central function to call the Groq API for generating
AI tutoring responses. Falls back to the template engine if no
API key is configured.

GDPR note: Only the current prompt and minimal context are sent
to the Groq API. No user PII (name, email, etc.) is transmitted.
Chat history is trimmed to the last few exchanges for context only.
"""
import logging
from typing import Optional

from groq import Groq, APIError, APIConnectionError, RateLimitError

from app.core.config import settings
from app.services.ai_engine import (
    build_system_prompt,
    detect_subject,
    generate_ai_response as template_response,
)

logger = logging.getLogger(__name__)

# Recommended Groq models (fastest → most capable)
# - llama-3.3-70b-versatile : best quality, German support
# - llama-3.1-8b-instant    : fastest, good for simple queries
# - mixtral-8x7b-32768      : good multilingual, large context
DEFAULT_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"
FAST_MODEL = "llama-3.1-8b-instant"
MAX_HISTORY_MESSAGES = 12  # Keep last 12 messages for context (GDPR: minimize data)
MAX_TOKENS = 2048

# Nuclear Reset Block A: Forbidden phrases that indicate generic theme lists
VERBOTENE_PHRASEN = [
    "ich kann dir helfen bei",
    "ich bin dein mathe-tutor",
    "hier sind themen die ich",
    "ich biete hilfe in folgenden",
    "stelle mir eine konkrete frage",
    "ich erkläre dir gerne",
    "welches thema möchtest du",
    "ich kann dir bei folgenden",
    "hier ist eine übersicht",
    "ich helfe dir gerne mit",
    "meine spezialgebiete",
]


def route_model(task_type: str) -> str:
    """Route to the best model based on task type (Model Routing).

    Simple questions -> fast model (cheaper, faster)
    Complex explanations, abitur -> quality model
    """
    fast_tasks = {"simple_question", "quiz_generation", "classification", "feedback"}
    if task_type in fast_tasks:
        return FAST_MODEL
    return DEFAULT_MODEL


def classify_needs_search(message: str) -> bool:
    """Quick heuristic to decide if a message needs web search.

    Avoids an extra LLM call -- uses keyword matching instead.
    """
    search_indicators = [
        "aktuell", "2024", "2025", "2026", "neuest", "letztes jahr",
        "reform", "gesetz", "statistik", "studie", "quelle", "forschung",
        "lehrplan", "curriculum", "abitur 20", "klausur 20",
        "was passiert", "warum ist", "wer hat", "wann wurde",
        "ereignis", "nachrichten", "politik",
    ]
    msg_lower = message.lower()
    return any(indicator in msg_lower for indicator in search_indicators)


def compress_history(chat_history: list) -> str:
    """Compress long chat history into a summary for context window optimization."""
    if not chat_history or len(chat_history) <= MAX_HISTORY_MESSAGES:
        return ""
    older = chat_history[:-MAX_HISTORY_MESSAGES]
    summary_parts = []
    for msg in older[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")[:100]
        if content:
            summary_parts.append(f"{role}: {content}")
    if summary_parts:
        return "BISHERIGER GESPRÄCHSVERLAUF (Zusammenfassung):\n" + "\n".join(summary_parts) + "\n---\n"
    return ""


def _get_client() -> Optional[Groq]:
    """Return a Groq client if an API key is configured, else None."""
    if not settings.GROQ_API_KEY:
        return None
    return Groq(api_key=settings.GROQ_API_KEY)


def _trim_history(chat_history: list, max_messages: int = MAX_HISTORY_MESSAGES) -> list:
    """Trim chat history to the last N messages for context.

    Only includes role and content — strips timestamps and metadata
    to comply with data minimization (GDPR).
    """
    if not chat_history:
        return []
    recent = chat_history[-max_messages:]
    return [
        {"role": msg.get("role", "user"), "content": msg.get("content", "")}
        for msg in recent
        if msg.get("content")
    ]


def call_groq_llm(
    prompt: str,
    system_prompt: str,
    subject: str,
    level: str,
    language: str = "de",
    chat_history: Optional[list] = None,
    model: Optional[str] = None,
    rag_context: str = "",
    is_pro: bool = False,
    temperature_override: Optional[float] = None,
    web_context: str = "",
    task_type: str = "explanation",
) -> str:
    """Call the Groq API to generate an AI tutoring response.

    Args:
        prompt: The user's message / question.
        system_prompt: Pre-built system prompt with subject, level, and rules.
        subject: Detected or selected subject (e.g. "math", "german").
        level: Student proficiency level ("beginner", "intermediate", "advanced").
        language: Response language ("de" or "en").
        chat_history: Previous messages in the session (trimmed for context).
        model: Override the default model.
        rag_context: Optional RAG-retrieved context to inject into the prompt.
        is_pro: Whether the user has a Pro subscription (affects temperature).

    Returns:
        The AI-generated response string.

    Raises:
        No exceptions — falls back to template engine on any error.
    """
    client = _get_client()
    if client is None:
        # No API key configured — use built-in template engine
        return template_response(
            message=prompt,
            subject=subject,
            level=level,
            language=language,
            chat_history=chat_history,
        )

    # Inject RAG context into system prompt if available
    if rag_context:
        system_prompt += (
            "\n\n--- Relevanter Kontext aus dem Lehrplan / Curriculum ---\n"
            f"{rag_context}\n"
            "--- Ende Kontext ---\n"
            "Nutze diesen Kontext um die Frage des Schülers zu beantworten. "
            "Nenne die Quellen wenn möglich."
        )

    # Inject web search context (Auto-Web-Search)
    if web_context:
        system_prompt += (
            "\n\n--- AKTUELLE INTERNET-QUELLEN (heute recherchiert) ---\n"
            f"{web_context}\n"
            "--- Ende Quellen ---\n"
            "Nutze diese aktuellen Quellen in deiner Antwort. "
            "Zitiere sie mit [1], [2], etc."
        )

    # Add compressed history summary for long conversations
    history_summary = compress_history(chat_history or [])
    if history_summary:
        system_prompt += f"\n{history_summary}"

    # Build messages list
    messages = [{"role": "system", "content": system_prompt}]

    # Add trimmed history for conversational context
    if chat_history:
        trimmed = _trim_history(chat_history)
        # Don't duplicate the current user message if it's already in history
        for msg in trimmed:
            if msg["content"] != prompt:
                messages.append(msg)

    # Add current user message
    messages.append({"role": "user", "content": prompt})

    # Model routing based on task type
    chosen_model = model or route_model(task_type)

    try:
        # Retry-Logik: bis zu 3 Versuche bei Timeout/Fehlern
        response_text = None
        last_err = None
        for attempt in range(3):
            try:
                completion = client.chat.completions.create(
                    model=chosen_model,
                    messages=messages,
                    max_tokens=MAX_TOKENS,
                    temperature=temperature_override if temperature_override is not None else (0.7 if is_pro else 0.3),
                    top_p=0.9,
                    stream=False,
                    timeout=30.0,
                )
                response_text = completion.choices[0].message.content
                if response_text:
                    break
            except Exception as retry_err:
                last_err = retry_err
                logger.warning("Groq attempt %d failed: %s", attempt + 1, retry_err)
                import asyncio
                import time
                time.sleep(1 * (attempt + 1))
        
        if not response_text and last_err:
            raise last_err  # type: ignore
        if response_text:
            cleaned = response_text.strip()
            # Nuclear Reset Block A: Check for forbidden generic theme lists
            cleaned_lower = cleaned.lower()
            if any(p in cleaned_lower for p in VERBOTENE_PHRASEN):
                logger.warning("Forbidden phrase detected in AI response, retrying with stricter prompt")
                # Retry with much stricter prompt forcing direct answer
                retry_messages = list(messages)  # copy
                retry_messages[-1] = {
                    "role": "user",
                    "content": (
                        f"WICHTIG: Beantworte NUR diese konkrete Frage direkt: {prompt}\n"
                        f"KEIN allgemeines Angebot, KEINE Themenliste — direkte Antwort!"
                    ),
                }
                try:
                    retry_completion = client.chat.completions.create(
                        model=DEFAULT_MODEL,
                        messages=retry_messages,
                        max_tokens=MAX_TOKENS,
                        temperature=0.5,
                        stream=False,
                    )
                    retry_text = retry_completion.choices[0].message.content
                    if retry_text:
                        return retry_text.strip()
                except Exception as retry_err:
                    logger.warning("Retry after forbidden phrase failed: %s", retry_err)
            return cleaned
        # Empty response — fall through to fallback
        logger.warning("Groq returned empty response, falling back to template engine")

    except RateLimitError:
        logger.warning("Groq rate limit hit, trying fallback model")
        try:
            completion = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=0.7,
                top_p=0.9,
                stream=False,
            )
            response_text = completion.choices[0].message.content
            if response_text:
                return response_text.strip()
        except Exception as fallback_err:
            logger.error("Fallback model also failed: %s", fallback_err)

    except (APIError, APIConnectionError) as api_err:
        logger.error("Groq API error: %s", api_err)

    except Exception as err:
        logger.error("Unexpected error calling Groq: %s", err)

    # Final fallback: template engine
    logger.info("Using template engine fallback for subject=%s", subject)
    return template_response(
        message=prompt,
        subject=subject,
        level=level,
        language=language,
        chat_history=chat_history,
    )


def deep_think_answer(
    prompt: str,
    system_prompt: str,
    subject: str,
    level: str,
    language: str = "de",
    chat_history: Optional[list] = None,
    rag_context: str = "",
    web_context: str = "",
    is_pro: bool = False,
    temperature_override: Optional[float] = None,
) -> str:
    """Final Polish 5.1 Block 6: Multi-Step Reasoning (ANALYSE -> ANTWORT -> CHECK).

    Step 1: Fast internal analysis using llama-3.1-8b-instant (cheap, fast)
    Step 2: Perfect answer using llama-3.3-70b-versatile with full system prompt
    The analysis informs the final answer but is NOT shown to the student.
    """
    client = _get_client()
    if client is None:
        # No API key — use standard call
        return call_groq_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            subject=subject,
            level=level,
            language=language,
            chat_history=chat_history,
            rag_context=rag_context,
            web_context=web_context,
            is_pro=is_pro,
            temperature_override=temperature_override,
        )

    # --- Step 1: ANALYSE (fast, cheap model) ---
    analyse_prompt = (
        f"Du bist ein Lehr-Analyse-Assistent. Analysiere INTERN folgende Schüler-Frage:\n"
        f"Fach: {subject} | Niveau: {level} | Sprache: {language}\n\n"
        f"Frage: {prompt}\n\n"
        f"Beantworte KURZ (max 3 Sätze):\n"
        f"1. Was ist das Kernthema?\n"
        f"2. Welches Vorwissen braucht der Schüler?\n"
        f"3. Häufige Fehler bei diesem Thema?"
    )

    analyse_result = ""
    try:
        analyse_completion = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": "Du bist ein interner Analyse-Assistent. Antworte kurz und präzise."},
                {"role": "user", "content": analyse_prompt},
            ],
            max_tokens=300,
            temperature=0.3,
            stream=False,
        )
        analyse_result = analyse_completion.choices[0].message.content or ""
        logger.debug("Deep think analyse: %s", analyse_result[:100])
    except Exception as e:
        logger.warning("Deep think analyse failed (non-fatal): %s", e)

    # --- Step 2: ANTWORT (quality model with analysis context) ---
    enhanced_system = system_prompt
    if analyse_result:
        enhanced_system += (
            f"\n\nINTERNE ANALYSE (nicht dem Schüler zeigen!):\n{analyse_result}\n"
            f"Nutze diese Analyse um eine perfekte, geprüft korrekte Antwort zu geben."
        )

    return call_groq_llm(
        prompt=prompt,
        system_prompt=enhanced_system,
        subject=subject,
        level=level,
        language=language,
        chat_history=chat_history,
        model=DEFAULT_MODEL,
        rag_context=rag_context,
        web_context=web_context,
        is_pro=is_pro,
        temperature_override=temperature_override,
        task_type="explanation",
    )
