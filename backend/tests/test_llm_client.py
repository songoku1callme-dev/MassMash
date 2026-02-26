"""Tests for the LLM client abstraction layer."""

import pytest
from app.llm.dummy import DummyProvider
from app.llm.factory import get_llm_provider
from app.llm.base import LLMProvider
from app.models.schemas import ChatMessage


@pytest.mark.asyncio
async def test_dummy_provider_returns_response():
    """Test that the dummy provider returns a valid response."""
    provider = DummyProvider()
    messages = [ChatMessage(role="user", content="Hallo, wie geht es dir?")]
    response = await provider.chat(messages)

    assert response.role == "assistant"
    assert len(response.content) > 0
    assert "Platzhalter" in response.content or "Dummy" in response.content


@pytest.mark.asyncio
async def test_dummy_provider_echoes_user_message():
    """Test that the dummy provider echoes back part of the user message."""
    provider = DummyProvider()
    test_msg = "Dies ist eine Testnachricht"
    messages = [ChatMessage(role="user", content=test_msg)]
    response = await provider.chat(messages)

    assert test_msg in response.content


@pytest.mark.asyncio
async def test_dummy_provider_with_system_prompt():
    """Test that the dummy provider acknowledges system prompts."""
    provider = DummyProvider()
    messages = [ChatMessage(role="user", content="Test")]
    response = await provider.chat(messages, system_prompt="Du bist ein Experte")

    assert "System-Prompt aktiv" in response.content


@pytest.mark.asyncio
async def test_dummy_provider_multi_turn():
    """Test multi-turn conversation picks the last user message."""
    provider = DummyProvider()
    messages = [
        ChatMessage(role="user", content="Erste Nachricht"),
        ChatMessage(role="assistant", content="Antwort"),
        ChatMessage(role="user", content="Zweite Nachricht"),
    ]
    response = await provider.chat(messages)

    assert "Zweite Nachricht" in response.content


def test_dummy_provider_name():
    """Test provider name and model name."""
    provider = DummyProvider()
    assert provider.provider_name() == "dummy"
    assert provider.model_name() == "dummy-v1"


def test_factory_returns_dummy_when_no_keys(monkeypatch):
    """Test that factory returns DummyProvider when no API keys are set."""
    monkeypatch.setattr("app.config.settings.LLM_PROVIDER", "openai")
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "")

    provider = get_llm_provider()
    assert isinstance(provider, DummyProvider)


def test_factory_returns_dummy_for_dummy_provider():
    """Test that factory returns DummyProvider for 'dummy' provider."""
    provider = get_llm_provider("dummy")
    assert isinstance(provider, DummyProvider)


def test_factory_returns_correct_type(monkeypatch):
    """Test that factory returns correct provider types when keys are set."""
    monkeypatch.setattr("app.config.settings.OPENAI_API_KEY", "test-key")
    provider = get_llm_provider("openai")
    assert provider.provider_name() == "openai"

    monkeypatch.setattr("app.config.settings.ANTHROPIC_API_KEY", "test-key")
    provider = get_llm_provider("anthropic")
    assert provider.provider_name() == "anthropic"


def test_llm_provider_is_abstract():
    """Test that LLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]
