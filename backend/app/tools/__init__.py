"""Tool-calling system for the AI Desktop Client."""

from app.tools.registry import tool_registry, get_tool_definitions

__all__ = ["tool_registry", "get_tool_definitions"]
