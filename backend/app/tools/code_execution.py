"""Safe code execution tool -- runs Python code in a restricted sandbox."""

import ast
import io
import contextlib
import math
import json
import datetime
from typing import Any

from app.tools.base import Tool
from app.tools.registry import tool_registry


# Allowlisted built-in names available inside the sandbox
_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "bool": bool,
    "chr": chr,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "hex": hex,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
}

# Modules that can be imported inside the sandbox
_ALLOWED_MODULES = {"math", "json", "datetime", "collections", "itertools", "re", "statistics"}


class CodeExecutionTool(Tool):
    """Execute Python code in a safe sandbox and return the output."""

    def name(self) -> str:
        return "code_execution"

    def description(self) -> str:
        return (
            "Execute Python code and return the printed output. "
            "Use this for calculations, data transformations, or quick scripts. "
            "The sandbox has access to math, json, datetime, collections, itertools, re, statistics."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use print() to produce output.",
                },
            },
            "required": ["code"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        code = arguments.get("code", "")
        if not code:
            return "Error: No code provided."

        # Basic static checks
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return f"SyntaxError: {exc}"

        # Reject dangerous constructs
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = ""
                if isinstance(node, ast.Import):
                    module_name = node.names[0].name.split(".")[0]
                elif node.module:
                    module_name = node.module.split(".")[0]
                if module_name not in _ALLOWED_MODULES:
                    return f"ImportError: Module '{module_name}' is not allowed in the sandbox."

            # Build a safe __import__ that only allows allowlisted modules
            def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
                top = name.split(".")[0]
                if top not in _ALLOWED_MODULES:
                    raise ImportError(f"Module '{name}' is not allowed in the sandbox.")
                return __builtins__["__import__"](name, *args, **kwargs) if isinstance(__builtins__, dict) else __import__(name, *args, **kwargs)  # type: ignore[index]

            # Build restricted globals
            sandbox_globals: dict[str, Any] = {"__builtins__": {**_SAFE_BUILTINS, "__import__": _safe_import}}
            sandbox_globals["math"] = math
            sandbox_globals["json"] = json
            sandbox_globals["datetime"] = datetime

        # Capture stdout
        stdout_capture = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout_capture):
                exec(compile(tree, "<sandbox>", "exec"), sandbox_globals)  # noqa: S102
        except Exception as exc:
            error_output = stdout_capture.getvalue()
            return f"{error_output}Error: {type(exc).__name__}: {exc}"

        output = stdout_capture.getvalue()
        if not output:
            # Try to return the value of the last expression
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                try:
                    result = eval(  # noqa: S307
                        compile(ast.Expression(tree.body[-1].value), "<sandbox>", "eval"),
                        sandbox_globals,
                    )
                    return str(result)
                except Exception:
                    pass
            return "(No output)"

        # Limit output length
        max_len = 5000
        if len(output) > max_len:
            output = output[:max_len] + "\n... (output truncated)"
        return output


# Auto-register
tool_registry.register(CodeExecutionTool())
