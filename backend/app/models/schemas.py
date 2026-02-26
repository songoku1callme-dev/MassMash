"""Pydantic schemas for request/response models."""

from pydantic import BaseModel
from typing import Any, Optional


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: str  # "user", "assistant", "system"
    content: str


class ToolCall(BaseModel):
    """A tool invocation requested by the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """The result of executing a tool."""
    tool_call_id: str
    name: str
    result: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    messages: list[ChatMessage]
    mode: str = "normal"  # "normal", "programmer", "document_analysis"
    system_prompt: Optional[str] = None
    file_context: Optional[str] = None
    enable_tools: bool = True


class ChatResponse(BaseModel):
    """Response body from chat endpoint."""
    message: ChatMessage
    provider: str
    model: str
    tool_calls: list[ToolCall] = []
    tool_results: list[ToolResult] = []


class FileUploadResponse(BaseModel):
    """Response body from file upload endpoint."""
    filename: str
    extracted_text: str
    char_count: int


class SettingsRequest(BaseModel):
    """Request body for updating settings."""
    llm_provider: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openai_base_url: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None


class SettingsResponse(BaseModel):
    """Response body with current settings (keys masked)."""
    llm_provider: str
    openai_api_key_set: bool
    openai_model: str
    openai_base_url: str
    gemini_api_key_set: bool
    gemini_model: str
    anthropic_api_key_set: bool
    anthropic_model: str
    ollama_base_url: str
    ollama_model: str


class OllamaModelInfo(BaseModel):
    """Information about a locally available Ollama model."""
    name: str
    size: int = 0
    digest: str = ""


class OllamaStatusResponse(BaseModel):
    """Health / status response for the Ollama server."""
    available: bool
    base_url: str
    models: list[OllamaModelInfo] = []
