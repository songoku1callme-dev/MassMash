"""Ollama router - health check and model listing for local Ollama server."""

from fastapi import APIRouter
from app.models.schemas import OllamaModelInfo, OllamaStatusResponse
from app.llm.ollama_provider import ollama_health_check, ollama_list_models
from app.config import settings

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/status", response_model=OllamaStatusResponse)
async def ollama_status() -> OllamaStatusResponse:
    """Check if the Ollama server is reachable and list available models."""
    available = await ollama_health_check()
    models: list[OllamaModelInfo] = []

    if available:
        raw_models = await ollama_list_models()
        models = [
            OllamaModelInfo(
                name=m.get("name", ""),
                size=m.get("size", 0),
                digest=m.get("digest", ""),
            )
            for m in raw_models
        ]

    return OllamaStatusResponse(
        available=available,
        base_url=settings.OLLAMA_BASE_URL,
        models=models,
    )
