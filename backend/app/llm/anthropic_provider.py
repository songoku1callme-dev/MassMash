"""Anthropic Claude LLM provider implementation."""

from anthropic import AsyncAnthropic
from app.llm.base import LLMProvider
from app.models.schemas import ChatMessage
from app.config import settings


class AnthropicProvider(LLMProvider):
    """LLM provider using the Anthropic Claude API."""

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> ChatMessage:
        api_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg.role in ("user", "assistant"):
                api_messages.append({"role": msg.role, "content": msg.content})

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": api_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)
        content = response.content[0].text if response.content else ""
        return ChatMessage(role="assistant", content=content)

    def provider_name(self) -> str:
        return "anthropic"

    def model_name(self) -> str:
        return self._model
