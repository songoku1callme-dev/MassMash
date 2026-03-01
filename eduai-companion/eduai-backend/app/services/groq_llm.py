"""Groq LLM integration for EduAI Companion.

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
MAX_HISTORY_MESSAGES = 10  # Keep last N messages for context (GDPR: minimize data)
MAX_TOKENS = 2048


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
            "\n\n--- RELEVANTER KONTEXT AUS DEM LEHRPLAN ---\n"
            f"{rag_context}\n"
            "--- ENDE KONTEXT ---\n\n"
            "WICHTIG: Nutze den obigen Lehrplan-Kontext um die Frage des Schülers "
            "präzise und lehrplankonform zu beantworten. "
            "Zitiere die Quelle wenn möglich (z.B. 'Laut Lehrplan Klasse 10...')."
        )

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

    chosen_model = model or DEFAULT_MODEL

    try:
        completion = client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            top_p=0.9,
            stream=False,
        )
        response_text = completion.choices[0].message.content
        if response_text:
            return response_text.strip()
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
