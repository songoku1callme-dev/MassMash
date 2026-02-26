"""OpenAI LLM provider implementation."""

from openai import AsyncOpenAI
from app.llm.base import LLMProvider
from app.models.schemas import ChatMessage
from app.config import settings


class OpenAIProvider(LLMProvider):
    """LLM provider using the OpenAI API (GPT models)."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._model = settings.OPENAI_MODEL

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

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=api_messages,  # type: ignore[arg-type]
        )

        content = response.choices[0].message.content or ""
        return ChatMessage(role="assistant", content=content)

    def provider_name(self) -> str:
        return "openai"

    def model_name(self) -> str:
        return self._model
