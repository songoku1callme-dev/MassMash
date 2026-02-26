"""Central registry that holds all available tools."""

from typing import Any

from app.tools.base import Tool


class ToolRegistry:
    """Stores tool instances by name and provides lookup helpers."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Add a tool to the registry."""
        self._tools[tool.name()] = tool

    def get(self, name: str) -> Tool | None:
        """Look up a tool by name."""
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible function definitions for all tools."""
        return [t.to_openai_schema() for t in self._tools.values()]


# ---------------------------------------------------------------------------
# Singleton registry -- tools are registered at import time
# ---------------------------------------------------------------------------
tool_registry = ToolRegistry()


def get_tool_definitions() -> list[dict[str, Any]]:
    """Convenience accessor for ``tool_registry.definitions()``."""
    return tool_registry.definitions()
