"""Tests for chat endpoints."""

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def authed_client():
    """Register a unique user and return an authenticated client."""
    uid = uuid.uuid4().hex[:8]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        reg_data = {
            "email": f"chat_{uid}@example.com",
            "username": f"chat_{uid}",
            "password": "TestPass123!",
            "full_name": "Chat Test User",
            "school_grade": "10",
            "school_type": "Gymnasium",
            "preferred_language": "de",
        }
        resp = await c.post("/api/auth/register", json=reg_data)
        data = resp.json()
        assert "access_token" in data, f"Registration failed: {data}"
        c.headers["Authorization"] = f"Bearer {data['access_token']}"
        yield c


@pytest.mark.asyncio
async def test_send_chat_message(authed_client: AsyncClient):
    resp = await authed_client.post(
        "/api/chat",
        json={
            "message": "Was ist der Satz des Pythagoras?",
            "subject": "math",
            "language": "de",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "session_id" in data
    # normalize_fach maps English names to German: "math" → "Mathematik"
    assert data["subject"] in ("math", "general", "Mathematik", "Allgemein")


@pytest.mark.asyncio
async def test_chat_sessions_list(authed_client: AsyncClient):
    # Send a message first to create a session
    await authed_client.post(
        "/api/chat",
        json={"message": "Hello", "language": "en"},
    )

    resp = await authed_client.get("/api/chat/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1


@pytest.mark.asyncio
async def test_chat_session_detail(authed_client: AsyncClient):
    # Create session
    resp = await authed_client.post(
        "/api/chat",
        json={"message": "Test message", "language": "de"},
    )
    session_id = resp.json()["session_id"]

    # Get session detail
    resp = await authed_client.get(f"/api/chat/sessions/{session_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert "messages" in detail
    assert len(detail["messages"]) >= 2  # user + assistant


@pytest.mark.asyncio
async def test_chat_without_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/chat", json={"message": "test"})
        assert resp.status_code in (401, 403)
