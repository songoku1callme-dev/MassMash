"""Dummy LLM provider for testing without API keys."""

from app.llm.base import LLMProvider
from app.models.schemas import ChatMessage


class DummyProvider(LLMProvider):
    """Returns canned responses when no real API key is configured."""

    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> ChatMessage:
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_msg = msg.content
                break

        response_text = (
            f"[Dummy-Modus] Ich habe deine Nachricht erhalten: \"{last_user_msg[:100]}...\"\n\n"
            "Dies ist eine Platzhalter-Antwort, da kein API-Key konfiguriert ist. "
            "Bitte gehe in die Einstellungen und trage deinen API-Key ein, "
            "um eine echte KI-Antwort zu erhalten.\n\n"
            "Unterstützte Provider: OpenAI, Google Gemini, Anthropic Claude."
        )

        if system_prompt:
            response_text = f"[System-Prompt aktiv: {system_prompt[:50]}...]\n\n{response_text}"

        return ChatMessage(role="assistant", content=response_text)

    def provider_name(self) -> str:
        return "dummy"

    def model_name(self) -> str:
        return "dummy-v1"
