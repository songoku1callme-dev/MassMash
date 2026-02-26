"""FastAPI application entry point for the AI Desktop Client backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, files, settings

app = FastAPI(
    title="MassMash AI Desktop Client",
    description="Backend for the AI Desktop Client with LLM integration",
    version="1.0.0",
)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Register routers
app.include_router(chat.router)
app.include_router(files.router)
app.include_router(settings.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
