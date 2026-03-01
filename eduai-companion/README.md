# EduAI Companion — KI-Tutor für deutsche Schüler

> **Production-Ready 1.0** — AI-powered tutoring for German students (Gymnasium/Realschule).

[![CI](https://github.com/songoku1callme-dev/MassMash/actions/workflows/ci.yml/badge.svg)](https://github.com/songoku1callme-dev/MassMash/actions)

---

## Features

| Feature | Status |
|---------|--------|
| **5 Fächer** (Mathe, Englisch, Deutsch, Geschichte, Naturwissenschaften) | Done |
| **Groq LLM** (llama-3.3-70b-versatile, Fallback auf Template-Engine) | Done |
| **RAG** (FAISS + sentence-transformers, 13 Lehrplandokumente) | Done |
| **OCR/Math-Solver** (Tesseract-deu + SymPy → KaTeX) | Done |
| **Speech-to-Text** (Web Speech API im Browser) | Done |
| **Quiz** (MCQ + Fill-in-blank, 3 Schwierigkeitsstufen, Server-Side Validation) | Done |
| **Lernpfad** (personalisierte Empfehlungen, Proficiency-Tracking) | Done |
| **PWA** (installierbar, Offline-Caching, Auto-Update) | Done |
| **JWT Auth** (Access 30min + Refresh 7d, Auto-Refresh) | Done |
| **Dark Mode** | Done |
| **Deutsche Umlaute** (äöüÄÖÜ überall korrekt) | Done |
| **Production Docker** (Tesseract-deu, FAISS, Health Checks) | Done |
| **PostgreSQL-Migration** (Schema vorbereitet) | Scaffolded |
| **Clerk OAuth** (Google Login vorbereitet, braucht Keys) | Scaffolded |
| **Sentry + PostHog** (Error-Tracking + Analytics vorbereitet) | Scaffolded |
| **Admin Stats** (/api/admin/stats) | Done |

---

## Schnellstart (5 Minuten)

### Voraussetzungen

- **Node.js** >= 18
- **Python** >= 3.12
- **Poetry** (`pip install poetry`)

### 1. Repository klonen

```bash
git clone https://github.com/songoku1callme-dev/MassMash.git
cd MassMash/eduai-companion
```

### 2. Backend starten

```bash
cd eduai-backend

# Dependencies installieren
poetry install

# Umgebungsvariablen konfigurieren
cp ../.env.template .env
# SECRET_KEY und optional GROQ_API_KEY eintragen

# Server starten
poetry run fastapi dev app/main.py
```

Backend läuft auf: `http://localhost:8000`
API-Docs: `http://localhost:8000/docs`

### 3. Frontend starten

```bash
cd eduai-frontend

# Dependencies installieren
npm install

# Server starten
npm run dev
```

Frontend läuft auf: `http://localhost:5173`

### 4. Alternativ: Docker Compose

```bash
cd eduai-companion
cp .env.template .env
# SECRET_KEY eintragen
docker compose up --build
```

Frontend: `http://localhost:5173` | Backend: `http://localhost:8000`

---

## Umgebungsvariablen

| Variable | Erforderlich | Beschreibung |
|----------|-------------|--------------|
| `SECRET_KEY` | **Ja** (Produktion) | JWT-Signatur. Generieren: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `GROQ_API_KEY` | Nein | Groq API Key für echte KI-Antworten. Ohne: Template-Engine als Fallback. |
| `EDUAI_DEV_MODE` | Nein | `1` = permissive CORS (alle Origins erlaubt) |
| `DATABASE_PATH` | Nein | SQLite-Pfad. Standard: `app.db` (lokal) oder `/data/app.db` (Fly.io) |
| `CLERK_PUBLISHABLE_KEY` | Nein | Clerk OAuth (https://dashboard.clerk.com) |
| `CLERK_SECRET_KEY` | Nein | Clerk OAuth Secret |
| `POSTHOG_API_KEY` | Nein | PostHog Analytics (https://posthog.com) |
| `SENTRY_DSN` | Nein | Sentry Error-Tracking (https://sentry.io) |

Siehe `.env.template` für die vollständige Liste.

---

## Groq LLM Setup

1. Account erstellen: [console.groq.com](https://console.groq.com/)
2. API Key generieren (kostenlos, beginnt mit `gsk_...`)
3. In `.env` eintragen: `GROQ_API_KEY=gsk_dein_key`

| Modell | Geschwindigkeit | Qualität | Empfohlen für |
|--------|----------------|----------|---------------|
| `llama-3.3-70b-versatile` | Mittel | Exzellent | Komplexe Erklärungen, Deutsch |
| `llama-3.1-8b-instant` | Sehr schnell | Gut | Einfache Fragen |
| `mixtral-8x7b-32768` | Mittel | Sehr gut | Multilingual, großer Kontext |

---

## API-Endpunkte

### Auth
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| POST | `/api/auth/register` | Neuen Nutzer registrieren |
| POST | `/api/auth/login` | Anmelden, Tokens erhalten |
| POST | `/api/auth/refresh` | Access Token erneuern |
| GET | `/api/auth/me` | Profil abrufen |
| PUT | `/api/auth/me` | Profil aktualisieren |
| GET | `/api/auth/clerk-config` | Clerk OAuth Status |

### Chat + KI
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| POST | `/api/chat` | Nachricht senden, KI-Antwort erhalten |
| GET | `/api/chat/sessions` | Chat-Sessions auflisten |
| GET | `/api/chat/sessions/{id}` | Session mit Nachrichten |
| DELETE | `/api/chat/sessions/{id}` | Session löschen |

### Quiz
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| POST | `/api/quiz/generate` | Quiz generieren (ohne Antworten!) |
| POST | `/api/quiz/check-answer` | Einzelne Antwort prüfen |
| POST | `/api/quiz/submit` | Quiz abgeben, Ergebnisse erhalten |
| GET | `/api/quiz/history` | Quiz-Verlauf |

### Lernpfad
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| GET | `/api/subjects` | Fächer auflisten |
| GET | `/api/profile` | Lernprofile |
| GET | `/api/progress` | Gesamtfortschritt |
| GET | `/api/learning-path/{subject}` | Lernpfad pro Fach |

### RAG (Wissensdatenbank)
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| POST | `/api/rag/index` | Dokument indexieren |
| POST | `/api/rag/query` | Ähnliche Dokumente suchen |
| POST | `/api/rag/upload` | Datei hochladen (txt/md/csv/pdf) |
| GET | `/api/rag/documents` | Alle Dokumente auflisten |
| DELETE | `/api/rag/documents/{id}` | Dokument löschen |
| GET | `/api/rag/stats` | RAG-Statistiken |
| POST | `/api/rag/seed` | Deutsche Lehrpläne laden |

### OCR + Math-Solver
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| POST | `/api/ocr/solve-image` | Bild → Gleichung erkennen → lösen |
| POST | `/api/ocr/solve-text` | Text → Gleichung parsen → lösen |

### Admin
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Plattform-Statistiken |
| GET | `/api/admin/monitoring-config` | Monitoring-Konfiguration |
| GET | `/healthz` | Health Check (DB, Version, Timestamp) |

---

## Projektstruktur

```
eduai-companion/
├── .env.template              # Alle Umgebungsvariablen dokumentiert
├── docker-compose.yml         # Lokales Setup (Backend + Frontend)
├── eduai-backend/
│   ├── Dockerfile             # Production Image (Tesseract + FAISS)
│   ├── .dockerignore
│   ├── fly.toml               # Fly.io Deployment (2GB RAM, Volume)
│   ├── pyproject.toml         # Python Dependencies
│   ├── app/
│   │   ├── main.py            # FastAPI Entry Point
│   │   ├── core/
│   │   │   ├── auth.py        # JWT (Access + Refresh Tokens)
│   │   │   ├── clerk.py       # Clerk OAuth Scaffolding
│   │   │   ├── config.py      # Settings aus Umgebungsvariablen
│   │   │   ├── database.py    # SQLite Setup
│   │   │   ├── migrate_postgres.py  # PostgreSQL-Migration
│   │   │   ├── monitoring.py  # Sentry + PostHog
│   │   │   └── security.py    # Rate Limiting, CSP, Security Headers
│   │   ├── models/
│   │   │   └── schemas.py     # Pydantic Request/Response Models
│   │   ├── routes/
│   │   │   ├── admin.py       # Admin Stats + Monitoring Config
│   │   │   ├── auth.py        # Auth + Clerk Config
│   │   │   ├── chat.py        # Chat + Groq LLM
│   │   │   ├── learning.py    # Lernpfad + Proficiency
│   │   │   ├── ocr.py         # OCR + Math-Solver
│   │   │   ├── quiz.py        # Quiz (Server-Side Validation)
│   │   │   └── rag.py         # RAG (FAISS + Upload)
│   │   └── services/
│   │       ├── ai_engine.py   # Template-Engine (Fallback)
│   │       ├── groq_llm.py    # Groq LLM Integration
│   │       ├── ocr_solver.py  # Tesseract + SymPy
│   │       ├── rag_service.py # FAISS RAG Service
│   │       └── seed_curriculum.py  # Deutsche Lehrplandaten
│   └── tests/                 # pytest (24+ Tests)
├── eduai-frontend/
│   ├── Dockerfile             # Dev Container (Node 20)
│   ├── src/
│   │   ├── pages/             # React Pages (7 Seiten)
│   │   ├── components/        # shadcn/ui Components
│   │   ├── hooks/             # Custom Hooks (Auth, Speech)
│   │   ├── stores/            # Zustand State Management
│   │   └── services/          # API Client
│   └── public/                # PWA Icons + Manifest
```

---

## Tests

```bash
# Backend (pytest)
cd eduai-backend
poetry run pytest tests/ -v
# Erwartet: 24+ Tests bestanden

# Frontend (vitest)
cd eduai-frontend
npm run test
# Erwartet: 15+ Tests bestanden

# Frontend Build
npm run build
# Erwartet: 0 Fehler
```

---

## Deployment

### Backend (Fly.io)

```bash
cd eduai-backend
fly deploy
# Setzt voraus: fly.toml konfiguriert, Secrets gesetzt
fly secrets set SECRET_KEY=dein_key GROQ_API_KEY=gsk_dein_key
```

### Frontend (Vercel)

```bash
cd eduai-frontend
vercel --prod
# Oder: Git Push → Vercel Auto-Deploy
```

### PostgreSQL-Migration

```bash
# Schema anzeigen:
python -m app.core.migrate_postgres

# Schema anwenden (DATABASE_URL muss gesetzt sein):
DATABASE_URL=postgresql://... python -m app.core.migrate_postgres --apply
```

---

## Sicherheit

- **JWT**: Access Token 30min, Refresh Token 7d
- **Rate Limiting**: 5 req/min auf Auth-Endpoints
- **Security Headers**: CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff
- **Quiz**: Antworten nur server-seitig validiert (kein Cheat möglich)
- **CORS**: In Produktion auf bekannte Origins beschränkt
- **Permissions-Policy**: Kamera + Mikrofon nur von gleicher Origin erlaubt

---

## Lizenz

MIT
