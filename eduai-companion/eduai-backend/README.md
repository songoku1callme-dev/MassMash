# EduAI Companion — Backend

AI-powered tutoring API for German students (Gymnasium/Realschule).  
Built with **FastAPI**, **SQLite** (aiosqlite), and optional **Groq LLM** integration.

---

## Quick Start

```bash
cd eduai-companion/eduai-backend

# Install dependencies
poetry install

# Configure environment
cp .env.example .env   # or edit .env directly
# Set SECRET_KEY and optionally GROQ_API_KEY (see below)

# Run the server
poetry run fastapi dev app/main.py
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | **Yes** (for production) | JWT signing key. Generate with: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. If unset, a random key is generated on each restart (sessions won't persist). |
| `GROQ_API_KEY` | No | Groq API key for real LLM responses. Without it, the built-in template engine is used as fallback. |
| `DATABASE_URL` | No | SQLite database path. Defaults to `app.db` (local) or `/data/app.db` (production with volume). |

### Example `.env`

```env
SECRET_KEY=your-strong-random-key-here
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Groq LLM Setup

The backend supports real AI responses via the [Groq API](https://groq.com/) (free tier available).

### 1. Get an API Key

1. Go to [console.groq.com](https://console.groq.com/)
2. Create an account (free)
3. Navigate to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

### 2. Set the Key

```bash
# In .env file
GROQ_API_KEY=gsk_your_key_here

# Or as environment variable
export GROQ_API_KEY=gsk_your_key_here
```

### 3. Recommended Models

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `llama-3.3-70b-versatile` | Medium | Excellent | Complex explanations, German language |
| `llama-3.1-8b-instant` | Very fast | Good | Simple questions, quick replies |
| `mixtral-8x7b-32768` | Medium | Very good | Multilingual, large context windows |

The default model is `llama-3.3-70b-versatile`. If rate-limited, the system automatically falls back to `llama-3.1-8b-instant`, then to the built-in template engine.

### 4. Running with LLM

```bash
# With GROQ_API_KEY set in .env:
poetry run fastapi dev app/main.py

# The chat endpoint will now use Groq for AI responses.
# If the key is missing or invalid, it falls back to template responses.
```

---

## Authentication

The API uses JWT tokens with short-lived access tokens and long-lived refresh tokens:

- **Access token**: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Refresh token**: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- **Refresh endpoint**: `POST /api/auth/refresh` with `{"refresh_token": "..."}`

---

## Quiz Security

Quiz answers are validated **server-side only**. The `/api/quiz/generate` endpoint returns questions without `correct_answer` or `explanation` fields. Answers are stored in the database and only revealed via:

- `POST /api/quiz/check-answer` — check a single answer
- `POST /api/quiz/submit` — submit all answers and get results

This prevents cheating via browser Network tab inspection.

---

## RAG Preparation (Future)

The `app/services/rag_service.py` module provides a clean interface for future vector store integration:

```python
from app.services.rag_service import rag_service

# Index a document
rag_service.index_document("doc1", "Content here...", {"subject": "math"})

# Search
results = rag_service.search_similar("quadratic equations", top_k=5)
```

Currently uses an in-memory dummy implementation. To integrate a real vector store:

1. Replace `DummyRAGService` with a Pinecone/FAISS/Chroma implementation
2. Keep the same `RAGServiceBase` interface
3. Swap the singleton in `rag_service.py`

### Planned Curriculum Data Sources

- **LehrplanPLUS Bayern**: https://www.lehrplanplus.bayern.de/
- **KMK Bildungsstandards**: https://www.kmk.org/
- **Bildungsserver Niedersachsen / Hessen**
- **Abitur exam archives** (past 5+ years, per Bundesland)
- **Khan Academy German transcripts**
- **Wikipedia.de** (filtered by education topics)

### Recommended Embedding Models

- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `deepset/gbert-base` (German BERT)
- `intfloat/multilingual-e5-large`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Get current user |
| PUT | `/api/auth/me` | Update profile |
| POST | `/api/chat` | Send message, get AI response |
| GET | `/api/chat/sessions` | List chat sessions |
| GET | `/api/chat/sessions/{id}` | Get session with messages |
| DELETE | `/api/chat/sessions/{id}` | Delete session |
| POST | `/api/quiz/generate` | Generate quiz (no answers in response) |
| POST | `/api/quiz/check-answer` | Check single answer |
| POST | `/api/quiz/submit` | Submit quiz, get results |
| GET | `/api/quiz/history` | Quiz history |
| GET | `/api/subjects` | List subjects |
| GET | `/api/profile` | Learning profiles |
| GET | `/api/progress` | Overall progress |
| GET | `/api/learning-path/{subject}` | Learning path |
| GET | `/healthz` | Health check |

---

## Project Structure

```
app/
├── core/
│   ├── auth.py          # JWT auth (access + refresh tokens)
│   ├── config.py        # Settings from environment
│   └── database.py      # SQLite setup
├── models/
│   └── schemas.py       # Pydantic request/response models
├── routes/
│   ├── auth.py          # Auth endpoints
│   ├── chat.py          # Chat endpoints
│   ├── quiz.py          # Quiz endpoints (server-side validation)
│   └── learning.py      # Learning path endpoints
├── services/
│   ├── ai_engine.py     # Template-based fallback engine
│   ├── groq_llm.py      # Groq LLM integration
│   └── rag_service.py   # RAG interface (dummy for now)
└── main.py              # FastAPI app entry point
```
