"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from app.models.schemas import ChatMessage


class LLMProvider(ABC):
    """Interface that all LLM providers must implement."""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> ChatMessage:
        """Send messages to the LLM and return the assistant's response.

        Args:
            messages: The conversation history.
            system_prompt: Optional system-level instruction.

        Returns:
            The assistant's response as a ChatMessage.
        """
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider (e.g. 'openai')."""
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier being used."""
        ...
