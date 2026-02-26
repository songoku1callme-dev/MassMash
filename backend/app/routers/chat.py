"""Chat router - handles LLM conversation endpoints."""

from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.llm import get_llm_provider

router = APIRouter(prefix="/api/chat", tags=["chat"])

# System prompts for different modes
MODE_SYSTEM_PROMPTS: dict[str, str] = {
    "normal": (
        "Du bist ein hilfreicher Assistent. Antworte klar, freundlich und "
        "präzise auf die Fragen des Nutzers."
    ),
    "programmer": (
        "Du bist ein erfahrener Programmier-Assistent. Hilf dem Nutzer beim "
        "Schreiben, Debuggen und Erklären von Code. Nutze Code-Blöcke mit "
        "Syntax-Highlighting. Erkläre deine Lösungen Schritt für Schritt."
    ),
    "document_analysis": (
        "Du bist ein Dokumenten-Analyse-Assistent. Der Nutzer wird dir Text "
        "aus Dokumenten bereitstellen. Analysiere den Inhalt gründlich, fasse "
        "zusammen, beantworte Fragen zum Text und identifiziere Kernaussagen."
    ),
}


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat request and return the LLM's response.

    Supports multi-turn conversation with configurable modes and system prompts.
    """
    try:
        provider = get_llm_provider()

        # Determine system prompt: custom > mode default
        system_prompt = request.system_prompt
        if not system_prompt:
            system_prompt = MODE_SYSTEM_PROMPTS.get(request.mode, MODE_SYSTEM_PROMPTS["normal"])

        # If file context is provided, prepend it to the system prompt
        if request.file_context:
            system_prompt += (
                "\n\n--- Dokument-Kontext ---\n"
                f"{request.file_context}\n"
                "--- Ende Dokument-Kontext ---"
            )

        response_message = await provider.chat(
            messages=request.messages,
            system_prompt=system_prompt,
        )

        return ChatResponse(
            message=response_message,
            provider=provider.provider_name(),
            model=provider.model_name(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
