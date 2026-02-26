"""Tests for the tool-calling system."""

import pytest
from app.tools.registry import ToolRegistry
from app.tools.base import Tool
from app.tools.web_search import WebSearchTool
from app.tools.code_execution import CodeExecutionTool
from app.tools.file_tools import FileListTool, FileReadTool
from app.tools import tool_registry, get_tool_definitions


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

def test_registry_register_and_get():
    """Test registering and retrieving a tool."""
    reg = ToolRegistry()
    tool = WebSearchTool()
    reg.register(tool)
    assert reg.get("web_search") is tool
    assert reg.get("nonexistent") is None


def test_registry_all():
    """Test listing all registered tools."""
    reg = ToolRegistry()
    reg.register(WebSearchTool())
    reg.register(CodeExecutionTool())
    assert len(reg.all()) == 2


def test_registry_definitions():
    """Test OpenAI-compatible definitions."""
    reg = ToolRegistry()
    reg.register(WebSearchTool())
    defs = reg.definitions()
    assert len(defs) == 1
    assert defs[0]["type"] == "function"
    assert defs[0]["function"]["name"] == "web_search"


def test_global_registry_has_all_tools():
    """Test that the global registry has all 4 tools auto-registered."""
    names = {t.name() for t in tool_registry.all()}
    assert "web_search" in names
    assert "code_execution" in names
    assert "file_list" in names
    assert "file_read" in names


def test_get_tool_definitions_returns_list():
    """Test convenience function."""
    defs = get_tool_definitions()
    assert isinstance(defs, list)
    assert len(defs) >= 4


# ---------------------------------------------------------------------------
# Web Search tool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_web_search_placeholder():
    """Test web search returns placeholder when no API key."""
    tool = WebSearchTool()
    result = await tool.execute({"query": "Berlin Wetter"})
    assert "Berlin Wetter" in result
    assert "Platzhalter" in result


@pytest.mark.asyncio
async def test_web_search_empty_query():
    """Test web search with empty query."""
    tool = WebSearchTool()
    result = await tool.execute({"query": ""})
    assert "Error" in result


def test_web_search_schema():
    """Test web search parameter schema."""
    tool = WebSearchTool()
    schema = tool.parameters_schema()
    assert schema["type"] == "object"
    assert "query" in schema["properties"]
    assert "query" in schema["required"]


# ---------------------------------------------------------------------------
# Code Execution tool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_code_execution_basic():
    """Test simple code execution."""
    tool = CodeExecutionTool()
    result = await tool.execute({"code": "print(2 + 2)"})
    assert "4" in result


@pytest.mark.asyncio
async def test_code_execution_math():
    """Test code execution with math module."""
    tool = CodeExecutionTool()
    result = await tool.execute({"code": "import math\nprint(math.sqrt(16))"})
    assert "4.0" in result


@pytest.mark.asyncio
async def test_code_execution_disallowed_import():
    """Test that disallowed imports are rejected."""
    tool = CodeExecutionTool()
    result = await tool.execute({"code": "import os\nprint(os.getcwd())"})
    assert "not allowed" in result


@pytest.mark.asyncio
async def test_code_execution_syntax_error():
    """Test syntax error handling."""
    tool = CodeExecutionTool()
    result = await tool.execute({"code": "def ("})
    assert "SyntaxError" in result


@pytest.mark.asyncio
async def test_code_execution_runtime_error():
    """Test runtime error handling."""
    tool = CodeExecutionTool()
    result = await tool.execute({"code": "print(1/0)"})
    assert "ZeroDivisionError" in result


@pytest.mark.asyncio
async def test_code_execution_expression_result():
    """Test that last expression is returned when no print."""
    tool = CodeExecutionTool()
    result = await tool.execute({"code": "2 + 3"})
    assert "5" in result


@pytest.mark.asyncio
async def test_code_execution_empty():
    """Test empty code input."""
    tool = CodeExecutionTool()
    result = await tool.execute({"code": ""})
    assert "Error" in result


# ---------------------------------------------------------------------------
# File List tool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_file_list_current_dir():
    """Test listing current directory."""
    tool = FileListTool()
    result = await tool.execute({"path": "."})
    assert "Contents of" in result


@pytest.mark.asyncio
async def test_file_list_nonexistent():
    """Test listing nonexistent directory."""
    tool = FileListTool()
    result = await tool.execute({"path": "/nonexistent/path"})
    assert "Error" in result


# ---------------------------------------------------------------------------
# File Read tool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_file_read_existing(tmp_path):
    """Test reading an existing file."""
    f = tmp_path / "test.txt"
    f.write_text("Hello World")
    tool = FileReadTool()
    result = await tool.execute({"path": str(f)})
    assert "Hello World" in result


@pytest.mark.asyncio
async def test_file_read_nonexistent():
    """Test reading nonexistent file."""
    tool = FileReadTool()
    result = await tool.execute({"path": "/nonexistent/file.txt"})
    assert "Error" in result


@pytest.mark.asyncio
async def test_file_read_empty_path():
    """Test reading with empty path."""
    tool = FileReadTool()
    result = await tool.execute({"path": ""})
    assert "Error" in result
