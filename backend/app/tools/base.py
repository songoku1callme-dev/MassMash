"""Base class for all tools."""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Interface that all tools must implement."""

    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool (e.g. 'web_search')."""
        ...

    @abstractmethod
    def description(self) -> str:
        """Human-readable description shown to the LLM."""
        ...

    @abstractmethod
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema describing the tool's input parameters."""
        ...

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> str:
        """Run the tool with the given arguments and return a text result.

        Args:
            arguments: Validated parameters matching ``parameters_schema``.

        Returns:
            A plain-text result string that will be fed back to the LLM.
        """
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """Return the tool definition in OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name(),
                "description": self.description(),
                "parameters": self.parameters_schema(),
            },
        }
