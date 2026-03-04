# Testing LUMNOS Frontend (EduAI Companion)

## Overview
LUMNOS is a German AI tutoring platform built with React + Vite (frontend) and FastAPI (backend). The frontend runs on port 5175, backend on port 8000.

## Devin Secrets Needed
- `GROQ_API_KEY` — Required for AI chat responses (Groq LLM API)
- No other secrets needed for local testing (dev auto-login is built in)

## Local Setup

### Backend
```bash
cd eduai-companion/eduai-backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd eduai-companion/eduai-frontend
npm run dev -- --port 5175 --host 0.0.0.0
```

### Auto-Login
The frontend has built-in dev auto-login (App.tsx). On first load, it creates a dev user in localStorage with:
- Email: admin@lumnos.de
- Username: TestAdmin
- Subscription: max tier
- No manual login needed for testing

## Key Testing Patterns

### Chat Page (KI-Tutor)
- Default page on load (currentPage="chat")
- Subject header with Fach categories at top
- Messages area in the middle (scrollable)
- Input textarea fixed at bottom (flexShrink: 0)
- Welcome screen shows "Was möchtest du wissen?" when no messages
- Enter = send message, Shift+Enter = new line
- Textarea auto-resizes up to 5 lines (120px max)
- AI responses stream via SSE from backend

### Navigation
- Sidebar on left with all navigation items
- Click sidebar buttons to switch pages
- Sidebar scrolls independently (middle section has overflowY: auto)
- User profile fixed at bottom of sidebar
- Logo/buttons fixed at top of sidebar

### Non-Chat Pages
- All wrapped in PageLayout component
- Each page scrolls within its own container
- No global scroll on html/body/#root (overflow: hidden)

## Common Issues

### Vite HMR Cache
If the page loads blank after code changes, check browser console for:
```
SyntaxError: The requested module '/src/App.tsx' does not provide an export named 'default'
```
Fix: Restart the Vite dev server (kill and re-run `npm run dev`)

### CSS Warning
`@import must precede all other statements` — This is a pre-existing warning in index.css related to Tailwind @import ordering. It does not affect functionality.

### Backend Connection
If chat messages fail to get AI responses, verify:
1. Backend is running on port 8000
2. GROQ_API_KEY is set in .env file
3. Frontend .env.local has correct VITE_API_URL

## Verification Checklist for Chat Layout
1. Input field stays at bottom regardless of message count
2. Sidebar scrolls independently without moving chat input
3. New messages trigger auto-scroll to bottom
4. Textarea grows with multi-line text (max 5 lines)
5. Enter sends, Shift+Enter creates newline
6. Empty chat shows welcome screen
7. Other pages (Dashboard, Quiz, etc.) scroll within their containers
8. No position animations (y/top/bottom) on input — only opacity/scale allowed
