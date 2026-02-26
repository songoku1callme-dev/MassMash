# MassMash AI Desktop Client

A full-featured AI chat application with LLM backend integration, file analysis, tool-calling, voice I/O, offline support, and a native desktop installer. Built with FastAPI, React, and Electron.

## Architecture Overview

```
MassMash/
├── backend/                    # Python/FastAPI Backend
│   ├── app/
│   │   ├── main.py            # FastAPI entry point + CORS
│   │   ├── config.py          # Configuration from ENV vars
│   │   ├── routers/
│   │   │   ├── chat.py        # Chat endpoint + Gaming/Hardware modi
│   │   │   ├── files.py       # File upload + text extraction
│   │   │   ├── tools.py       # Tool-calling endpoint
│   │   │   ├── ollama.py      # Ollama status/models endpoint
│   │   │   └── settings.py    # Runtime settings management
│   │   ├── llm/
│   │   │   ├── base.py        # LLMProvider abstract interface
│   │   │   ├── factory.py     # Provider factory (auto-selects provider)
│   │   │   ├── dummy.py       # Dummy provider (no API key needed)
│   │   │   ├── openai_provider.py    # OpenAI GPT integration
│   │   │   ├── gemini_provider.py    # Google Gemini integration
│   │   │   ├── anthropic_provider.py # Anthropic Claude integration
│   │   │   └── ollama_provider.py    # Ollama local/offline integration
│   │   ├── tools/
│   │   │   ├── base.py        # Tool base class
│   │   │   ├── registry.py    # Tool registry
│   │   │   ├── web_search.py  # Web search tool (Tavily)
│   │   │   ├── code_execution.py # Sandboxed code execution
│   │   │   └── file_tools.py  # File list/read tools
│   │   ├── file_handling/
│   │   │   └── parser.py      # Text extraction (PDF, TXT, DOCX)
│   │   └── models/
│   │       └── schemas.py     # Pydantic request/response models
│   └── tests/                 # Pytest test suite (56 tests)
├── frontend/                  # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx            # Main app with chat logic + export/import
│       ├── contexts/
│       │   └── ThemeContext.tsx    # Dark/Light theme provider
│       ├── components/
│       │   ├── Sidebar.tsx        # Conversations + export/import + theme toggle
│       │   ├── ChatMessage.tsx    # Message display + TTS button
│       │   ├── ChatInput.tsx      # Input + file upload + mic button
│       │   ├── ModeSelector.tsx   # 5 mode tabs with icons
│       │   ├── SettingsDialog.tsx  # Settings + Ollama + Voice config
│       │   └── LoadingDots.tsx    # Loading animation
│       ├── hooks/
│       │   ├── useSpeechRecognition.ts  # Web Speech Recognition
│       │   └── useSpeechSynthesis.ts    # Web Speech Synthesis (TTS)
│       ├── services/api.ts    # Backend API client
│       └── types/index.ts     # TypeScript types
├── electron/                  # Electron desktop wrapper + installer
│   ├── main.js               # Main process (splash, backend, auto-update)
│   ├── preload.js            # Secure bridge
│   ├── splash.html           # Splash screen (loading animation)
│   ├── icon.png              # App icon (512x512)
│   ├── icon.ico              # Windows icon (multi-size)
│   └── package.json          # Electron config + builder + NSIS
├── LICENSE                    # MIT License
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
| **Desktop** | Electron + electron-builder | Mature, NSIS installer for Windows, DMG for Mac |
| **Auto-Update** | electron-updater | Seamless updates via GitHub Releases |
| **File Parsing** | pdfplumber, python-docx | Reliable text extraction from PDF and DOCX |
| **Voice** | Web Speech API | Browser-native speech recognition + TTS |

## Features

- **Multi-turn Chat** with conversation history (persisted in localStorage)
- **5 Modes**: Normal Chat, Programming Assistant, Document Analysis, Gaming Optimizer, Hardware Advisor
- **Tool-Calling**: Web Search, Code Execution, File Read/List
- **Voice I/O**: Microphone input (Web Speech Recognition) + Text-to-Speech per message
- **File Upload & Analysis**: PDF, TXT, DOCX support with automatic text extraction
- **LLM Provider Abstraction**: OpenAI, Gemini, Anthropic, Ollama (offline), or Dummy
- **Ollama Offline Mode**: Local LLM via Ollama with auto-detect and cloud fallback
- **Chat Export/Import**: Save and load conversations as JSON files
- **Dark/Light Theme**: Toggle with localStorage persistence
- **Settings UI**: Configure API keys, models, providers, voice settings at runtime
- **Desktop Installer**: Windows EXE (NSIS), macOS DMG, Linux AppImage
- **Auto-Update**: Automatic updates via GitHub Releases
- **Splash Screen**: Animated loading screen while backend starts

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

# Start desktop app (backend starts automatically!)
npm start
```

> **Note:** The Electron app automatically starts the FastAPI backend, waits for it to be healthy via `/healthz`, and opens the window. If the backend crashes, it auto-restarts (up to 5 times). No need to start the backend separately!
>
> In **development mode** (`npm run start:dev`), the frontend Vite dev server should still be started separately (`cd frontend && npm run dev`).
> In **production mode** (packaged app), both backend and frontend are bundled.

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

### Build Desktop Installer

**Prerequisites:** Python 3.11+ with Poetry, Node.js 18+ with npm.

#### Windows (EXE Installer)
```bash
# 1. Install backend dependencies
cd backend && poetry install && cd ..

# 2. Build frontend
cd frontend && npm install && npm run build && cd ..

# 3. Build Windows installer
cd electron && npm install && npm run build:win
# Output: electron/dist/MassMash-AI-Setup-1.0.0.exe
```

#### macOS (DMG)
```bash
cd electron && npm run build:mac
# Output: electron/dist/MassMash-AI-Setup-1.0.0.dmg
```

#### Linux (AppImage)
```bash
cd electron && npm run build:linux
# Output: electron/dist/MassMash-AI-Setup-1.0.0.AppImage
```

#### All Platforms
```bash
cd electron && npm run build:all
```

### Unpacked Build (for testing, no installer)
```bash
cd electron && npm run package:win   # or package:mac / package:linux
# Output: electron/dist/win-unpacked/MassMash AI.exe
```

## Installing on Other PCs

### From Installer (recommended)

1. Download `MassMash-AI-Setup-1.0.0.exe` from [GitHub Releases](https://github.com/songoku1callme-dev/MassMash/releases)
2. Run the installer - it will guide you through the setup
3. Choose your installation directory (default: `C:\Users\<User>\AppData\Local\MassMash AI`)
4. A desktop shortcut and Start Menu entry will be created
5. Launch "MassMash AI" from your desktop or Start Menu

**Requirements on the target PC:**
- **Python 3.11+** with [Poetry](https://python-poetry.org/) installed and in PATH
- The app will start the backend server automatically on launch

### Auto-Update

Once installed, the app checks for updates automatically via GitHub Releases. When a new version is available:
1. The update downloads in the background
2. A dialog asks "Jetzt neustarten?" (Restart now?)
3. Click "Jetzt neustarten" to update, or it installs on next restart

### Publishing a New Release

```bash
cd electron

# Bump version in package.json, then:
npm run publish
# This builds + uploads to GitHub Releases
# Requires GH_TOKEN environment variable
```

## NSIS Installer Features

- Custom installation directory selection
- Desktop shortcut + Start Menu shortcut
- Uninstaller included
- Per-user installation (no admin required)
- Splash screen during backend startup
- App icon in taskbar and window

## Adding a New LLM Provider

1. Create `backend/app/llm/your_provider.py`
2. Implement the `LLMProvider` interface (see `base.py`)
3. Add configuration to `config.py`
4. Register in `factory.py`

## License

MIT - see [LICENSE](LICENSE)
