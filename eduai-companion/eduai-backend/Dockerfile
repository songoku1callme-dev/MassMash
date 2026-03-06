# syntax=docker/dockerfile:1

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PORT=8080

# System dependencies:
# - tesseract-ocr + language data for German OCR
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

# Railway sets PORT as env var; Fly.io uses 8080 via fly.toml
# Shell form so $PORT is expanded at runtime (defaults to 8080)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
