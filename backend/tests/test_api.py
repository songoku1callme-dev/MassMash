"""Integration tests for API endpoints."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_healthz():
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_dummy():
    """Test chat endpoint with dummy provider."""
    response = client.post("/api/chat/", json={
        "messages": [{"role": "user", "content": "Hallo!"}],
        "mode": "normal",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "dummy"
    assert data["message"]["role"] == "assistant"
    assert len(data["message"]["content"]) > 0


def test_chat_endpoint_with_file_context():
    """Test chat endpoint with file context."""
    response = client.post("/api/chat/", json={
        "messages": [{"role": "user", "content": "Fasse den Text zusammen"}],
        "mode": "document_analysis",
        "file_context": "Dies ist ein Testdokument mit wichtigem Inhalt.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["message"]["role"] == "assistant"


def test_chat_endpoint_programmer_mode():
    """Test chat endpoint in programmer mode."""
    response = client.post("/api/chat/", json={
        "messages": [{"role": "user", "content": "Schreibe eine Python Funktion"}],
        "mode": "programmer",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "dummy"


def test_get_settings():
    """Test getting current settings."""
    response = client.get("/api/settings/")
    assert response.status_code == 200
    data = response.json()
    assert "llm_provider" in data
    assert "openai_api_key_set" in data
    assert "openai_model" in data


def test_update_settings():
    """Test updating settings."""
    response = client.put("/api/settings/", json={
        "llm_provider": "openai",
        "openai_model": "gpt-4",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["llm_provider"] == "openai"
    assert data["openai_model"] == "gpt-4"


def test_file_upload_txt():
    """Test file upload with a text file."""
    content = "Dies ist ein Testinhalt fuer den Upload."
    response = client.post(
        "/api/files/upload",
        files={"file": ("test.txt", content.encode(), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert "Testinhalt" in data["extracted_text"]
    assert data["char_count"] > 0


def test_file_upload_unsupported():
    """Test file upload with unsupported format."""
    response = client.post(
        "/api/files/upload",
        files={"file": ("test.xyz", b"test content", "application/octet-stream")},
    )
    assert response.status_code == 400
