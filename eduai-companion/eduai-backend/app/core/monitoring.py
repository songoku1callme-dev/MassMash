"""Monitoring integration: Sentry (errors) + PostHog (analytics).

Activate by setting the corresponding environment variables:
  - SENTRY_DSN  → Sentry error tracking
  - POSTHOG_API_KEY + POSTHOG_HOST → PostHog product analytics

Both integrations are optional and GDPR-compliant (anonymous by default).
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
SENTRY_ENABLED = bool(SENTRY_DSN)


def init_sentry() -> None:
    """Initialize Sentry SDK if SENTRY_DSN is set."""
    if not SENTRY_ENABLED:
        logger.info("Sentry is DISABLED (SENTRY_DSN not set).")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
            ],
            traces_sample_rate=0.2,  # 20% of requests traced
            profiles_sample_rate=0.1,
            send_default_pii=False,  # GDPR: no PII by default
            environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        )
        logger.info("Sentry error tracking ENABLED.")
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed. "
            "Run: poetry add sentry-sdk[fastapi]"
        )


# ---------------------------------------------------------------------------
# PostHog
# ---------------------------------------------------------------------------

POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://eu.posthog.com")
POSTHOG_ENABLED = bool(POSTHOG_API_KEY)

_posthog_client = None


def init_posthog() -> None:
    """Initialize PostHog client if POSTHOG_API_KEY is set."""
    global _posthog_client

    if not POSTHOG_ENABLED:
        logger.info("PostHog analytics is DISABLED (POSTHOG_API_KEY not set).")
        return

    try:
        import posthog

        posthog.api_key = POSTHOG_API_KEY
        posthog.host = POSTHOG_HOST
        posthog.disabled = False
        _posthog_client = posthog
        logger.info("PostHog analytics ENABLED (host: %s).", POSTHOG_HOST)
    except ImportError:
        logger.warning(
            "POSTHOG_API_KEY is set but posthog is not installed. "
            "Run: poetry add posthog"
        )


def track_event(
    distinct_id: str,
    event: str,
    properties: Optional[dict] = None,
) -> None:
    """Track an analytics event in PostHog (no-op if disabled).

    Args:
        distinct_id: Anonymous user identifier (e.g. hashed user ID).
        event: Event name, e.g. "quiz_completed", "chat_message_sent".
        properties: Optional dict of event properties.
    """
    if _posthog_client is None:
        return
    try:
        _posthog_client.capture(
            distinct_id=distinct_id,
            event=event,
            properties=properties or {},
        )
    except Exception as exc:
        logger.warning("PostHog tracking error: %s", exc)


def shutdown_posthog() -> None:
    """Flush and shutdown PostHog client."""
    if _posthog_client is not None:
        try:
            _posthog_client.flush()
            _posthog_client.shutdown()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Frontend config (safe to expose)
# ---------------------------------------------------------------------------

def get_monitoring_frontend_config() -> dict:
    """Return monitoring config for the frontend (safe to expose).

    Reads env vars at request time so that test fixtures can override them.
    """
    sentry_dsn = os.getenv("SENTRY_DSN", "")
    posthog_key = os.getenv("POSTHOG_API_KEY", "")
    posthog_host = os.getenv("POSTHOG_HOST", "https://eu.posthog.com")
    return {
        "sentry_enabled": bool(sentry_dsn),
        "posthog_enabled": bool(posthog_key),
        "posthog_host": posthog_host if posthog_key else "",
        "posthog_api_key": posthog_key if posthog_key else "",
    }
