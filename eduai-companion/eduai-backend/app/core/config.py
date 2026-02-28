"""Application configuration."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings loaded from environment variables."""
    APP_NAME: str = "EduAI Companion"
    SECRET_KEY: str = "eduai-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    DATABASE_URL: str = ""
    GROQ_API_KEY: str = ""

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
