"""File system tools -- list and read local files for the user."""

import os
from typing import Any

from app.tools.base import Tool
from app.tools.registry import tool_registry


class FileListTool(Tool):
    """List files in a directory."""

    def name(self) -> str:
        return "file_list"

    def description(self) -> str:
        return (
            "List files and directories at a given path. "
            "Use this when the user wants to explore their local file system."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: current working directory).",
                },
            },
            "required": [],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        target = arguments.get("path", ".")

        if not os.path.exists(target):
            return f"Error: Path '{target}' does not exist."
        if not os.path.isdir(target):
            return f"Error: '{target}' is not a directory."

        try:
            entries = sorted(os.listdir(target))
        except PermissionError:
            return f"Error: Permission denied for '{target}'."

        if not entries:
            return f"Directory '{target}' is empty."

        lines: list[str] = [f"Contents of {os.path.abspath(target)}:\n"]
        for entry in entries[:100]:  # limit to 100 entries
            full = os.path.join(target, entry)
            kind = "DIR " if os.path.isdir(full) else "FILE"
            try:
                size = os.path.getsize(full) if os.path.isfile(full) else 0
                lines.append(f"  [{kind}] {entry}  ({size:,} bytes)" if size else f"  [{kind}] {entry}")
            except OSError:
                lines.append(f"  [{kind}] {entry}")

        if len(entries) > 100:
            lines.append(f"\n  ... and {len(entries) - 100} more entries")

        return "\n".join(lines)


class FileReadTool(Tool):
    """Read the contents of a text file."""

    def name(self) -> str:
        return "file_read"

    def description(self) -> str:
        return (
            "Read the contents of a text file. "
            "Use this when the user asks you to look at a specific file on their system."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read.",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default: 200).",
                },
            },
            "required": ["path"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        path = arguments.get("path", "")
        max_lines = arguments.get("max_lines", 200)

        if not path:
            return "Error: No file path provided."
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        if not os.path.isfile(path):
            return f"Error: '{path}' is not a file."

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"\n... (truncated after {max_lines} lines)")
                        break
                    lines.append(line)

            content = "".join(lines)
            if not content.strip():
                return f"File '{path}' is empty."

            return f"Contents of {path}:\n\n{content}"
        except PermissionError:
            return f"Error: Permission denied for '{path}'."
        except Exception as exc:
            return f"Error reading file: {exc}"


# Auto-register both tools
tool_registry.register(FileListTool())
tool_registry.register(FileReadTool())
