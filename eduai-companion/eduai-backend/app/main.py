import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import init_db
from app.core.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    ALLOWED_ORIGINS,
)
from app.routes import auth, chat, quiz, learning, rag, ocr, admin, memory, abitur, research, gamification, groups, tournaments, iq_test, flashcards, notes, referral, password_reset, calendar, multiplayer, legal, adaptive, school, intelligence, pomodoro, shop, challenges
from app.routes import stripe_routes
from app.core.monitoring import init_sentry, init_posthog, shutdown_posthog


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and monitoring on startup."""
    init_sentry()
    init_posthog()
    await init_db()
    yield
    shutdown_posthog()


app = FastAPI(
    title="EduAI Companion",
    description="AI-powered tutoring for German students",
    version="1.0.0",
    lifespan=lifespan
)

# --- Security middleware (outermost first) ---
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS — restrict to known frontend origins in production, allow all in dev
_cors_origins: list[str] = ["*"] if os.getenv("EDUAI_DEV_MODE") else ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(learning.router)
app.include_router(rag.router)
app.include_router(ocr.router)
app.include_router(admin.router)
app.include_router(memory.router)
app.include_router(abitur.router)
app.include_router(research.router)
app.include_router(stripe_routes.router)
app.include_router(gamification.router)
app.include_router(groups.router)
app.include_router(tournaments.router)
app.include_router(iq_test.router)
app.include_router(flashcards.router)
app.include_router(notes.router)
app.include_router(referral.router)
app.include_router(password_reset.router)
app.include_router(calendar.router)
app.include_router(multiplayer.router)
app.include_router(legal.router)
app.include_router(adaptive.router)
app.include_router(school.router)
app.include_router(intelligence.router)
app.include_router(pomodoro.router)
app.include_router(shop.router)
app.include_router(challenges.router)


@app.get("/healthz")
async def healthz():
    """Production health check used by Fly.io and monitoring."""
    import time

    checks: dict[str, str] = {}
    # DB connectivity
    try:
        import aiosqlite

        db_path = os.getenv("DATABASE_PATH", "app.db")
        async with aiosqlite.connect(db_path) as db:
            await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {
        "status": overall,
        "version": app.version,
        "checks": checks,
        "timestamp": int(time.time()),
    }
