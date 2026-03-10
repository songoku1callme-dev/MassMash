# syntax=docker/dockerfile:1
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PR #46: Zero-Budget 512MB RAM Dockerfile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PORT=8080 \
    # 512MB RAM optimization: limit Python memory
    MALLOC_TRIM_THRESHOLD_=65536 \
    PYTHONMALLOC=malloc

# System dependencies (minimal for 512MB):
# - tesseract-ocr installed only if OCR needed (lazy-loaded at runtime)
# - libgomp1 for faiss-cpu
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        tesseract-ocr \
        tesseract-ocr-deu \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (used only at build-time; deps installed into system site-packages)
RUN pip install --no-cache-dir poetry==1.8.3

WORKDIR /app

# Install python deps first (better layer caching)
COPY pyproject.toml poetry.lock /app/
RUN poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY app /app/app

EXPOSE 8080

# 512MB RAM: Single worker, no reload, minimal memory
# Shell form so $PORT is expanded at runtime (defaults to 8080)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --limit-max-requests 1000
