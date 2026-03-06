"""Shared test fixtures."""

import os
import asyncio
import tempfile

# Use a temp file for the test database (writable path) — must be set before app import
_test_db = os.path.join(tempfile.gettempdir(), "test_lumnos.db")
os.environ["DATABASE_URL"] = _test_db
os.environ["LUMNOS_DEV_MODE"] = "1"

# Force-import app.main so load_dotenv() runs NOW (before we clear secrets)
import app.main  # noqa: F401 — triggers load_dotenv

# Clear secrets AFTER dotenv loaded them so monitoring/clerk tests see "disabled" state
os.environ.pop("SENTRY_DSN", None)
os.environ.pop("CLERK_SECRET_KEY", None)
os.environ.pop("CLERK_PUBLISHABLE_KEY", None)
os.environ.pop("POSTHOG_API_KEY", None)

import pytest
from app.core.database import init_db
from app.core.security import _rate_limit_store, _endpoint_stores


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
    """Clear ALL rate limit stores before each test so tests don't interfere."""
    _rate_limit_store.clear()
    _endpoint_stores.clear()
    yield
