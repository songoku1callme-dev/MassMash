"""Tools router - lists available tools."""

from typing import Any
from fastapi import APIRouter

# Import tools so they auto-register
import app.tools.web_search  # noqa: F401
import app.tools.code_execution  # noqa: F401
import app.tools.file_tools  # noqa: F401
from app.tools import tool_registry

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/")
async def list_tools() -> list[dict[str, Any]]:
    """Return the list of available tools with their schemas."""
    return [
        {
            "name": t.name(),
            "description": t.description(),
            "parameters": t.parameters_schema(),
        }
        for t in tool_registry.all()
    ]
