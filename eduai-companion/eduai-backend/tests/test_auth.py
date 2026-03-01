"""Tests for authentication endpoints."""

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
async def test_healthz(client: AsyncClient):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    reg_data = {
        "email": "test_auth@example.com",
        "username": "test_auth_user",
        "password": "TestPass123!",
        "full_name": "Test Auth User",
        "school_grade": "10",
        "school_type": "Gymnasium",
        "preferred_language": "de",
    }
    resp = await client.post("/api/auth/register", json=reg_data)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "test_auth_user"

    # Login
    login_data = {"username": "test_auth_user", "password": "TestPass123!"}
    resp = await client.post("/api/auth/login", json=login_data)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    access_token = data["access_token"]

    # Get profile
    resp = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "test_auth@example.com"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    reg_data = {
        "email": "dup@example.com",
        "username": "dup_user",
        "password": "TestPass123!",
        "full_name": "Dup User",
        "school_grade": "10",
        "school_type": "Gymnasium",
        "preferred_language": "de",
    }
    resp = await client.post("/api/auth/register", json=reg_data)
    assert resp.status_code == 200

    # Try again with same username
    resp = await client.post("/api/auth/register", json=reg_data)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    # Register first
    reg_data = {
        "email": "wrongpw@example.com",
        "username": "wrongpw_user",
        "password": "CorrectPass123!",
        "full_name": "WrongPW User",
        "school_grade": "10",
        "school_type": "Gymnasium",
        "preferred_language": "de",
    }
    await client.post("/api/auth/register", json=reg_data)

    # Login with wrong password
    resp = await client.post(
        "/api/auth/login", json={"username": "wrongpw_user", "password": "WrongPass!"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    reg_data = {
        "email": "refresh@example.com",
        "username": "refresh_user",
        "password": "TestPass123!",
        "full_name": "Refresh User",
        "school_grade": "10",
        "school_type": "Gymnasium",
        "preferred_language": "de",
    }
    resp = await client.post("/api/auth/register", json=reg_data)
    data = resp.json()
    refresh_token = data["refresh_token"]

    # Use refresh token
    resp = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code in (401, 403)  # No auth header
