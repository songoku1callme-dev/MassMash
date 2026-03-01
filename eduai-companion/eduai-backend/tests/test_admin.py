"""Tests for admin stats and monitoring config endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_admin_stats(client: AsyncClient):
    """Admin stats endpoint returns expected structure."""
    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "total_chat_sessions" in data
    assert "total_quizzes" in data
    assert "avg_quiz_score" in data
    assert "proficiency_distribution" in data
    assert "subject_popularity" in data
    assert "activity_last_24h" in data
    # Values should be non-negative integers/floats
    assert data["total_users"] >= 0
    assert data["total_quizzes"] >= 0
    assert isinstance(data["avg_quiz_score"], (int, float))


@pytest.mark.asyncio
async def test_admin_stats_after_registration(client: AsyncClient):
    """Admin stats reflect new user after registration."""
    # Get initial count
    resp = await client.get("/api/admin/stats")
    initial_users = resp.json()["total_users"]

    # Register a new user
    reg_data = {
        "email": "admin_test@example.com",
        "username": "admin_test_user",
        "password": "TestPass123!",
        "full_name": "Admin Test",
        "school_grade": "10",
        "school_type": "Gymnasium",
        "preferred_language": "de",
    }
    await client.post("/api/auth/register", json=reg_data)

    # Stats should now show one more user
    resp = await client.get("/api/admin/stats")
    assert resp.json()["total_users"] == initial_users + 1


@pytest.mark.asyncio
async def test_monitoring_config(client: AsyncClient):
    """Monitoring config endpoint returns expected structure."""
    resp = await client.get("/api/admin/monitoring-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "sentry_enabled" in data
    assert "posthog_enabled" in data
    assert "posthog_host" in data
    assert "posthog_api_key" in data
    # Without keys set, both should be disabled
    assert data["sentry_enabled"] is False
    assert data["posthog_enabled"] is False


@pytest.mark.asyncio
async def test_clerk_config(client: AsyncClient):
    """Clerk config endpoint returns expected structure."""
    resp = await client.get("/api/auth/clerk-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "publishable_key" in data
    # Without keys set, Clerk should be disabled
    assert data["enabled"] is False
    assert data["publishable_key"] == ""
