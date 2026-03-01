"""Shared test fixtures."""

import os
import asyncio
import tempfile

# Use a temp file for the test database (writable path) — must be set before app import
_test_db = os.path.join(tempfile.gettempdir(), "test_eduai.db")
os.environ["DATABASE_URL"] = _test_db
os.environ["EDUAI_DEV_MODE"] = "1"

import pytest
from app.core.database import init_db
from app.core.security import _rate_limit_store


@pytest.fixture(autouse=True, scope="session")
def _setup_db():
    """Remove stale test database and initialize tables before the test session."""
    if os.path.exists(_test_db):
        os.remove(_test_db)
    # Initialize DB tables (lifespan doesn't fire with ASGITransport)
    asyncio.get_event_loop().run_until_complete(init_db())
    yield
    if os.path.exists(_test_db):
        os.remove(_test_db)


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Clear rate limit store before each test so tests don't interfere."""
    _rate_limit_store.clear()
    yield
