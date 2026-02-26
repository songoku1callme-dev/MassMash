"""Tests for the Ollama LLM provider and endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response, Request

from app.llm.ollama_provider import OllamaProvider, ollama_health_check, ollama_list_models
from app.models.schemas import ChatMessage


# ---------------------------------------------------------------------------
# OllamaProvider unit tests
# ---------------------------------------------------------------------------

def test_ollama_provider_name():
    """Test provider name."""
    provider = OllamaProvider()
    assert provider.provider_name() == "ollama"


def test_ollama_model_name():
    """Test model name returns configured model."""
    provider = OllamaProvider()
    assert isinstance(provider.model_name(), str)
    assert len(provider.model_name()) > 0


@pytest.mark.asyncio
async def test_ollama_chat_success():
    """Test successful chat with mocked Ollama API."""
    provider = OllamaProvider()

    mock_response = Response(
        200,
        json={
            "message": {"role": "assistant", "content": "Hallo! Mir geht es gut."},
            "done": True,
        },
        request=Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("app.llm.ollama_provider.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await provider.chat(
            messages=[ChatMessage(role="user", content="Hallo")],
            system_prompt="Du bist ein Assistent.",
        )

    assert result.role == "assistant"
    assert result.content == "Hallo! Mir geht es gut."


@pytest.mark.asyncio
async def test_ollama_chat_with_tools_returns_no_tool_calls():
    """Test that chat_with_tools falls back to normal chat (no native tool support)."""
    provider = OllamaProvider()

    mock_response = Response(
        200,
        json={
            "message": {"role": "assistant", "content": "Antwort"},
            "done": True,
        },
        request=Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("app.llm.ollama_provider.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        msg, tool_calls = await provider.chat_with_tools(
            messages=[ChatMessage(role="user", content="Test")],
            tool_definitions=[{"type": "function", "function": {"name": "test"}}],
        )

    assert msg is not None
    assert msg.content == "Antwort"
    assert tool_calls == []


@pytest.mark.asyncio
async def test_ollama_chat_with_tool_results():
    """Test chat_with_tool_results generates response incorporating results."""
    provider = OllamaProvider()

    mock_response = Response(
        200,
        json={
            "message": {"role": "assistant", "content": "Ergebnis verarbeitet."},
            "done": True,
        },
        request=Request("POST", "http://localhost:11434/api/chat"),
    )

    with patch("app.llm.ollama_provider.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await provider.chat_with_tool_results(
            messages=[ChatMessage(role="user", content="Test")],
            tool_results_text="Result: 42",
        )

    assert result.role == "assistant"
    assert result.content == "Ergebnis verarbeitet."


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ollama_health_check_online():
    """Test health check when Ollama is online."""
    mock_response = Response(
        200,
        text="Ollama is running",
        request=Request("GET", "http://localhost:11434"),
    )

    with patch("app.llm.ollama_provider.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await ollama_health_check()

    assert result is True


@pytest.mark.asyncio
async def test_ollama_health_check_offline():
    """Test health check when Ollama is not running."""
    import httpx

    with patch("app.llm.ollama_provider.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await ollama_health_check()

    assert result is False


# ---------------------------------------------------------------------------
# Model listing tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ollama_list_models_success():
    """Test listing models when Ollama is available."""
    mock_response = Response(
        200,
        json={
            "models": [
                {"name": "llama3.2", "size": 4_000_000_000, "digest": "abc123"},
                {"name": "mistral", "size": 3_800_000_000, "digest": "def456"},
            ]
        },
        request=Request("GET", "http://localhost:11434/api/tags"),
    )

    with patch("app.llm.ollama_provider.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        models = await ollama_list_models()

    assert len(models) == 2
    assert models[0]["name"] == "llama3.2"
    assert models[1]["name"] == "mistral"


@pytest.mark.asyncio
async def test_ollama_list_models_offline():
    """Test listing models when Ollama is offline returns empty list."""
    import httpx

    with patch("app.llm.ollama_provider.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        models = await ollama_list_models()

    assert models == []


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ollama_status_endpoint_offline():
    """Test the /api/ollama/status endpoint when Ollama is offline."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch("app.routers.ollama.ollama_health_check", return_value=False):
            resp = await client.get("/api/ollama/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert data["models"] == []


@pytest.mark.asyncio
async def test_ollama_status_endpoint_online():
    """Test the /api/ollama/status endpoint when Ollama is online."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    mock_models = [{"name": "llama3.2", "size": 4000000000, "digest": "abc"}]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch("app.routers.ollama.ollama_health_check", return_value=True), \
             patch("app.routers.ollama.ollama_list_models", return_value=mock_models):
            resp = await client.get("/api/ollama/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert len(data["models"]) == 1
    assert data["models"][0]["name"] == "llama3.2"


# ---------------------------------------------------------------------------
# Factory test
# ---------------------------------------------------------------------------

def test_factory_returns_ollama_provider():
    """Test that the factory returns OllamaProvider when configured."""
    from app.llm.factory import get_llm_provider

    provider = get_llm_provider("ollama")
    assert isinstance(provider, OllamaProvider)
    assert provider.provider_name() == "ollama"


# ---------------------------------------------------------------------------
# Settings tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_settings_include_ollama_fields():
    """Test that the settings endpoint includes Ollama fields."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/settings/")

    assert resp.status_code == 200
    data = resp.json()
    assert "ollama_base_url" in data
    assert "ollama_model" in data


@pytest.mark.asyncio
async def test_settings_update_ollama():
    """Test updating Ollama settings."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.put(
            "/api/settings/",
            json={"ollama_base_url": "http://myhost:11434", "ollama_model": "mistral"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ollama_base_url"] == "http://myhost:11434"
    assert data["ollama_model"] == "mistral"
