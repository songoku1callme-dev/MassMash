"""Dummy LLM provider for testing without API keys."""

import uuid
from app.llm.base import LLMProvider
from app.models.schemas import ChatMessage, ToolCall


# Patterns that should trigger tool calls in dummy mode
_TOOL_TRIGGERS: dict[str, dict] = {
    "web_search": {
        "keywords": ["suche", "search", "wetter", "weather", "news", "nachrichten", "aktuell", "preis", "price"],
        "make_args": lambda msg: {"query": msg},
    },
    "code_execution": {
        "keywords": ["berechne", "calculate", "rechne", "execute", "code", "python", "programmiere"],
        "make_args": lambda msg: {"code": 'print("Hello from the sandbox!")'},
    },
    "file_list": {
        "keywords": ["dateien", "files", "verzeichnis", "directory", "ordner", "folder", "liste"],
        "make_args": lambda _: {"path": "."},
    },
    "file_read": {
        "keywords": ["lies", "read", "datei lesen", "inhalt", "content", "zeig mir"],
        "make_args": lambda _: {"path": "README.md"},
    },
}


def _detect_tool_call(user_message: str) -> ToolCall | None:
    """Heuristically detect if the user message should trigger a tool call."""
    lower = user_message.lower()
    for tool_name, cfg in _TOOL_TRIGGERS.items():
        if any(kw in lower for kw in cfg["keywords"]):
            return ToolCall(
                id=f"call_{uuid.uuid4().hex[:8]}",
                name=tool_name,
                arguments=cfg["make_args"](user_message),
            )
    return None


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
            "Unterstuetzte Provider: OpenAI, Google Gemini, Anthropic Claude."
        )

        if system_prompt:
            response_text = f"[System-Prompt aktiv: {system_prompt[:50]}...]\n\n{response_text}"

        return ChatMessage(role="assistant", content=response_text)

    async def chat_with_tools(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
        tool_definitions: list[dict] | None = None,
    ) -> tuple[ChatMessage | None, list[ToolCall]]:
        """Dummy implementation that detects tool-trigger keywords."""
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_msg = msg.content
                break

        if tool_definitions:
            tool_call = _detect_tool_call(last_user_msg)
            if tool_call:
                return None, [tool_call]

        # No tool call detected -- fall back to normal chat
        msg = await self.chat(messages, system_prompt)
        return msg, []

    async def chat_with_tool_results(
        self,
        messages: list[ChatMessage],
        tool_results_text: str,
        system_prompt: str | None = None,
    ) -> ChatMessage:
        """Generate a response that incorporates tool results."""
        return ChatMessage(
            role="assistant",
            content=(
                f"[Dummy-Modus] Hier sind die Tool-Ergebnisse:\n\n{tool_results_text}\n\n"
                "Basierend auf diesen Ergebnissen wuerde ein echtes LLM jetzt eine "
                "ausfuehrliche Antwort generieren. Konfiguriere einen API-Key fuer echte Antworten."
            ),
        )

    def provider_name(self) -> str:
        return "dummy"

    def model_name(self) -> str:
        return "dummy-v1"
