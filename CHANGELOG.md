# Changelog

All notable changes to the MassMash AI Desktop Client will be documented in this file.

## [1.0.0] - 2026-02-26

### Initial Release

The first public release of MassMash AI - a full-featured AI desktop client with LLM backend, tool-calling, voice I/O, offline support, and native desktop installer.

### Features

#### Core Chat (PR #1)
- Multi-turn chat with conversation history (persisted in localStorage)
- LLM Provider abstraction: OpenAI GPT, Google Gemini, Anthropic Claude, Dummy fallback
- File upload and analysis: PDF, TXT, DOCX with automatic text extraction
- 3 base modes: Normal Chat, Programming Assistant, Document Analysis
- Settings UI: API key management, model selection, provider switching
- FastAPI backend with async processing
- React + Vite + TypeScript + Tailwind CSS frontend

#### Desktop Auto-Start (PR #2)
- Single-command launch: `npm start` starts everything
- Health-check polling on `/healthz` (up to 30s)
- Auto-restart on backend crash (up to 5 attempts)
- Windows-compatible process management (`taskkill`)
- Window shows only after content is ready (no white flash)

#### Tool-Calling (PR #3)
- Web Search tool (Tavily API placeholder, works with `SEARCH_API_KEY`)
- Code Execution tool (sandboxed Python with RestrictedPython)
- File List and File Read tools for local filesystem
- Tool registry with automatic keyword-based triggering
- Visual tool-call badges and result blocks in chat UI
- 42 backend tests (20 new tool tests)

#### Voice I/O (PR #4)
- Microphone input via Web Speech Recognition API
- Text-to-Speech per assistant message via Web Speech Synthesis
- Voice settings: language (8 languages), speed, pitch, voice selection
- Auto-read toggle for automatic TTS on new responses
- Red pulse animation on active microphone
- All settings persisted in localStorage

#### Ollama Offline Support (PR #5)
- New LLM Provider: Ollama (localhost:11434)
- Auto-detect available models with live status indicator
- Graceful fallback to Dummy provider when Ollama is unavailable
- Connection test button in settings
- Model dropdown auto-populated from Ollama API
- 56 backend tests total (14 new Ollama tests)

#### Gaming & Hardware Modes (PR #6)
- **PC Gaming Optimizer**: Expert for Fortnite/Warzone/Minecraft, monitor ghosting, network optimization, AMD GPU/CPU tweaks
- **Hardware Advisor**: CPU/GPU buying advice, PC building, upgrade paths, compatibility checks
- Custom German system prompts with Oldenburg student context
- Gamepad2 and Cpu icons in mode selector

#### Chat Export/Import (PR #6)
- Export all conversations as dated JSON file
- Import conversations from JSON with deduplication by ID
- Download and Upload buttons in sidebar

#### Dark/Light Theme (PR #6)
- Sun/Moon toggle in sidebar header
- Theme persisted in localStorage
- Theme-aware styling across all major components
- ThemeContext provider with React Context API

#### Desktop Installer & Release (PR #7)
- **Windows**: NSIS installer (.exe) with custom install directory, desktop/start menu shortcuts
- **macOS**: DMG installer with drag-to-Applications
- **Linux**: AppImage for portable execution
- Animated splash screen with purple gradient while backend starts
- Auto-update via electron-updater + GitHub Releases
- App icons: 512x512 PNG + multi-size ICO (16-256px)
- Build scripts: `npm run build:win`, `build:mac`, `build:linux`, `build:all`
- `npm run publish` for GitHub Release upload

#### Release Polish (PR #8)
- CHANGELOG.md with complete feature history
- GitHub Actions workflow for automated release builds
- Version 1.0.0 finalized

### Technical Details

- **Backend**: Python 3.11+ / FastAPI / Poetry
- **Frontend**: React 18 / Vite / TypeScript / Tailwind CSS
- **Desktop**: Electron 28 / electron-builder 24 / electron-updater 6
- **Tests**: 56 pytest tests covering LLM providers, tools, file parsing, API endpoints
- **CI/CD**: Vercel preview deployments + GitHub Actions release builds

### Known Limitations

- The packaged desktop app requires Python 3.11+ with Poetry installed on the target PC
- Voice I/O requires browser microphone permission (Electron prompts automatically)
- Ollama offline mode requires Ollama to be installed and running separately
- Theme does not yet cover SettingsDialog, LoadingDots, ToolCallBadge, ToolResultBlock components
- Chat import has minimal validation (array check only)

---

[1.0.0]: https://github.com/songoku1callme-dev/MassMash/releases/tag/v1.0.0
