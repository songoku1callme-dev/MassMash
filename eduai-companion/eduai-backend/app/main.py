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
from app.routes import auth, chat, quiz, learning, rag, ocr


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


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


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
