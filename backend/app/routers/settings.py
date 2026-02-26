"""Settings router - handles runtime configuration updates."""

from fastapi import APIRouter
from app.models.schemas import SettingsRequest, SettingsResponse
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    """Return the current settings (API keys are masked)."""
    return SettingsResponse(
        llm_provider=settings.LLM_PROVIDER,
        openai_api_key_set=bool(settings.OPENAI_API_KEY),
        openai_model=settings.OPENAI_MODEL,
        openai_base_url=settings.OPENAI_BASE_URL,
        gemini_api_key_set=bool(settings.GEMINI_API_KEY),
        gemini_model=settings.GEMINI_MODEL,
        anthropic_api_key_set=bool(settings.ANTHROPIC_API_KEY),
        anthropic_model=settings.ANTHROPIC_MODEL,
    )


@router.put("/", response_model=SettingsResponse)
async def update_settings(req: SettingsRequest) -> SettingsResponse:
    """Update runtime settings. Changes are kept in memory (not persisted to .env).

    The frontend stores API keys locally and sends them when updating settings.
    """
    if req.llm_provider is not None:
        settings.LLM_PROVIDER = req.llm_provider
    if req.openai_api_key is not None:
        settings.OPENAI_API_KEY = req.openai_api_key
    if req.openai_model is not None:
        settings.OPENAI_MODEL = req.openai_model
    if req.openai_base_url is not None:
        settings.OPENAI_BASE_URL = req.openai_base_url
    if req.gemini_api_key is not None:
        settings.GEMINI_API_KEY = req.gemini_api_key
    if req.gemini_model is not None:
        settings.GEMINI_MODEL = req.gemini_model
    if req.anthropic_api_key is not None:
        settings.ANTHROPIC_API_KEY = req.anthropic_api_key
    if req.anthropic_model is not None:
        settings.ANTHROPIC_MODEL = req.anthropic_model

    return SettingsResponse(
        llm_provider=settings.LLM_PROVIDER,
        openai_api_key_set=bool(settings.OPENAI_API_KEY),
        openai_model=settings.OPENAI_MODEL,
        openai_base_url=settings.OPENAI_BASE_URL,
        gemini_api_key_set=bool(settings.GEMINI_API_KEY),
        gemini_model=settings.GEMINI_MODEL,
        anthropic_api_key_set=bool(settings.ANTHROPIC_API_KEY),
        anthropic_model=settings.ANTHROPIC_MODEL,
    )
