"""Google Gemini LLM provider implementation."""

import google.generativeai as genai
from app.llm.base import LLMProvider
from app.models.schemas import ChatMessage
from app.config import settings


class GeminiProvider(LLMProvider):
    """LLM provider using the Google Gemini API."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model_name = settings.GEMINI_MODEL
        self._model = genai.GenerativeModel(self._model_name)

    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> ChatMessage:
        # Build conversation parts for Gemini
        parts: list[str] = []

        if system_prompt:
            parts.append(f"System instruction: {system_prompt}\n\n")

        for msg in messages:
            prefix = "User" if msg.role == "user" else "Assistant"
            parts.append(f"{prefix}: {msg.content}")

        prompt = "\n\n".join(parts)
        prompt += "\n\nAssistant:"

        response = self._model.generate_content(prompt)
        content = response.text or ""
        return ChatMessage(role="assistant", content=content)

    def provider_name(self) -> str:
        return "gemini"

    def model_name(self) -> str:
        return self._model_name
