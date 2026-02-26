"""Factory for creating LLM provider instances."""

from app.llm.base import LLMProvider
from app.config import settings


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """Create and return an LLM provider based on configuration.

    Args:
        provider_name: Override the configured provider. If None, uses settings.

    Returns:
        An instance of the requested LLM provider.
    """
    name = (provider_name or settings.LLM_PROVIDER).lower()

    if name == "openai" and settings.OPENAI_API_KEY:
        from app.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if name == "gemini" and settings.GEMINI_API_KEY:
        from app.llm.gemini_provider import GeminiProvider
        return GeminiProvider()

    if name == "anthropic" and settings.ANTHROPIC_API_KEY:
        from app.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()

    if name == "ollama":
        # Try Ollama – no API key needed, just a running server
        from app.llm.ollama_provider import OllamaProvider
        return OllamaProvider()

    # Fallback to dummy if provider not configured or no API key
    from app.llm.dummy import DummyProvider
    return DummyProvider()
