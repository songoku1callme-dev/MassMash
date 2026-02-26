"""Pydantic schemas for request/response models."""

from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    messages: list[ChatMessage]
    mode: str = "normal"  # "normal", "programmer", "document_analysis"
    system_prompt: Optional[str] = None
    file_context: Optional[str] = None


class ChatResponse(BaseModel):
    """Response body from chat endpoint."""
    message: ChatMessage
    provider: str
    model: str


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
