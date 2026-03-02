"""Application configuration.

SECRET_KEY must be set via environment variable in production.
Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"
"""
import os
import secrets
import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Marker value — if SECRET_KEY equals this, we know it was never overridden
_INSECURE_DEFAULT = "__CHANGE_ME_IN_PRODUCTION__"


class Settings(BaseSettings):
    """App settings loaded from environment variables."""
    APP_NAME: str = "Lumnos Companion"
    SECRET_KEY: str = _INSECURE_DEFAULT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Short-lived access token (30 min)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Refresh token valid for 7 days
    DATABASE_URL: str = ""
    GROQ_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_WEBHOOK_SECRET_1: str = ""
    STRIPE_WEBHOOK_SECRET_2: str = ""
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    # Perfect School 4.1 Block 6: PostgreSQL + Redis scaffolding
    POSTGRES_URL: str = ""  # e.g. postgresql+asyncpg://user:pass@host/db
    REDIS_URL: str = ""  # e.g. redis://localhost:6379/0

    class Config:
        env_file = ".env"
        extra = "allow"

    @property
    def db_path(self) -> str:
        """Get database path - use /data/app.db for persistent storage."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # Check if running in production with volume mount
        if os.path.exists("/data"):
            return "/data/app.db"
        return "app.db"


settings = Settings()

# If no SECRET_KEY was provided, generate a random one and warn
if settings.SECRET_KEY == _INSECURE_DEFAULT:
    settings.SECRET_KEY = secrets.token_urlsafe(64)
    logger.warning(
        "SECRET_KEY not set — using auto-generated random key. "
        "Sessions will NOT survive restarts. "
        "Set SECRET_KEY in .env or environment for production."
    )
