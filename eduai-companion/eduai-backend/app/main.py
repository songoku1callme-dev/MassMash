from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import init_db
from app.routes import auth, chat, quiz, learning


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

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(learning.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
