# MassMash AI Desktop Client

A full-featured AI chat application with LLM backend integration, file analysis capabilities, and a native desktop wrapper. Built with FastAPI, React, and Electron.

## Architecture Overview

```
MassMash/
├── backend/                    # Python/FastAPI Backend
│   ├── app/
│   │   ├── main.py            # FastAPI entry point + CORS
│   │   ├── config.py          # Configuration from ENV vars
│   │   ├── routers/
│   │   │   ├── chat.py        # Chat endpoint (LLM interaction)
│   │   │   ├── files.py       # File upload + text extraction
│   │   │   └── settings.py    # Runtime settings management
│   │   ├── llm/
│   │   │   ├── base.py        # LLMProvider abstract interface
│   │   │   ├── factory.py     # Provider factory (auto-selects provider)
│   │   │   ├── dummy.py       # Dummy provider (no API key needed)
│   │   │   ├── openai_provider.py    # OpenAI GPT integration
│   │   │   ├── gemini_provider.py    # Google Gemini integration
│   │   │   └── anthropic_provider.py # Anthropic Claude integration
│   │   ├── file_handling/
│   │   │   └── parser.py      # Text extraction (PDF, TXT, DOCX)
│   │   └── models/
│   │       └── schemas.py     # Pydantic request/response models
│   └── tests/                 # Pytest test suite (22 tests)
├── frontend/                  # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx            # Main app with chat logic
│       ├── components/        # UI components
│       │   ├── Sidebar.tsx        # Conversation list
│       │   ├── ChatMessage.tsx    # Message display
│       │   ├── ChatInput.tsx      # Input + file upload
│       │   ├── ModeSelector.tsx   # Mode tabs
│       │   ├── SettingsDialog.tsx  # Settings modal
│       │   └── LoadingDots.tsx    # Loading animation
│       ├── services/api.ts    # Backend API client
│       └── types/index.ts     # TypeScript types
├── electron/                  # Electron desktop wrapper
│   ├── main.js               # Main process (window + backend)
│   ├── preload.js            # Secure bridge
│   └── package.json          # Electron config + builder
├── start.sh                  # Start script (Linux/macOS)
├── start.bat                 # Start script (Windows)
└── README.md
```

## Tech Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| **Backend** | Python / FastAPI | Async, great ecosystem for PDF/DOCX parsing, easy API development |
| **Frontend** | React + Vite + TypeScript | Modern, fast HMR, type safety |
| **Styling** | Tailwind CSS | Utility-first, rapid UI development |
| **Desktop** | Electron | Mature, well-supported on Windows/macOS/Linux |
| **File Parsing** | pdfplumber, python-docx | Reliable text extraction from PDF and DOCX |

## Features

- **Multi-turn Chat** with conversation history (persisted in localStorage)
- **3 Modes**: Normal Chat, Programming Assistant, Document Analysis
- **File Upload & Analysis**: PDF, TXT, DOCX support with automatic text extraction
- **LLM Provider Abstraction**: Switch between OpenAI, Gemini, Anthropic, or Dummy
- **Settings UI**: Configure API keys, models, and providers at runtime
- **Dark Theme**: Modern dark UI with smooth animations
- **Desktop App**: Electron wrapper for native Windows/macOS/Linux experience

## Quick Start

### Prerequisites

- **Python 3.11+** with [Poetry](https://python-poetry.org/)
- **Node.js 18+** with npm
- (Optional) Electron for desktop mode

### 1. Clone & Setup

```bash
git clone https://github.com/songoku1callme-dev/MassMash.git
cd MassMash
```

### 2. Backend Setup

```bash
cd backend

# Copy environment config
cp .env.example .env
# Edit .env to add your API keys (optional - works with dummy mode)

# Install dependencies
poetry install

# Start the backend
poetry run fastapi dev app/main.py --port 8000
```

The backend will be available at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 4. (Optional) Desktop Mode with Electron

```bash
cd electron

# Install Electron
npm install

# Make sure backend and frontend are running, then:
npm start
```

### Quick Start Scripts

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```bat
start.bat
```

## Environment Variables (.env)

Copy `backend/.env.example` to `backend/.env` and configure:

```env
# LLM Provider: "openai", "gemini", "anthropic", "dummy"
LLM_PROVIDER=dummy

# OpenAI
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# Google Gemini
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-1.5-flash

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# File Upload
MAX_FILE_SIZE_MB=10
```

> **Note:** Without API keys, the app runs in **Dummy mode** and returns placeholder responses. This is perfect for testing the UI and functionality.

## Running Tests

```bash
cd backend
poetry run pytest tests/ -v
```

All 22 tests cover:
- LLM client abstraction (dummy provider, factory, multi-turn)
- File parser (TXT, DOCX, unicode, unsupported formats)
- API endpoints (chat, file upload, settings, health check)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/healthz` | Health check |
| `POST` | `/api/chat/` | Send chat message to LLM |
| `POST` | `/api/files/upload` | Upload file for text extraction |
| `GET` | `/api/settings/` | Get current settings |
| `PUT` | `/api/settings/` | Update settings |

## Building for Production

### Frontend Build
```bash
cd frontend
npm run build
# Output in frontend/dist/
```

### Electron Package (Windows)
```bash
cd electron
npm run package:win
# Output in electron/dist/
```

## Adding a New LLM Provider

1. Create `backend/app/llm/your_provider.py`
2. Implement the `LLMProvider` interface (see `base.py`)
3. Add configuration to `config.py`
4. Register in `factory.py`

## License

MIT
