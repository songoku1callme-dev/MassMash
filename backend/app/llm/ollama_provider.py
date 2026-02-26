"""Ollama LLM provider for local/offline model inference."""

import httpx
from app.llm.base import LLMProvider
from app.models.schemas import ChatMessage, ToolCall
from app.config import settings


class OllamaProvider(LLMProvider):
    """LLM provider using a local Ollama server (http://localhost:11434)."""

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL

    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> ChatMessage:
        api_messages: list[dict[str, str]] = []

        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": api_messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        content = data.get("message", {}).get("content", "")
        return ChatMessage(role="assistant", content=content)

    async def chat_with_tools(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
        tool_definitions: list[dict] | None = None,
    ) -> tuple[ChatMessage | None, list[ToolCall]]:
        """Ollama does not natively support tool-calling in all models.

        We fall back to normal chat and let the dummy tool-detection layer
        handle keyword-based triggering if needed.
        """
        msg = await self.chat(messages, system_prompt)
        return msg, []

    async def chat_with_tool_results(
        self,
        messages: list[ChatMessage],
        tool_results_text: str,
        system_prompt: str | None = None,
    ) -> ChatMessage:
        """Generate a response that incorporates tool results."""
        augmented = list(messages) + [
            ChatMessage(
                role="assistant",
                content=f"Tool-Ergebnisse:\n{tool_results_text}",
            )
        ]
        return await self.chat(augmented, system_prompt)

    def provider_name(self) -> str:
        return "ollama"

    def model_name(self) -> str:
        return self._model


async def ollama_health_check(base_url: str | None = None) -> bool:
    """Return True if the Ollama server is reachable."""
    url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
        return False


async def ollama_list_models(base_url: str | None = None) -> list[dict]:
    """Fetch the list of locally available models from Ollama."""
    url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return data.get("models", [])
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
        return []
