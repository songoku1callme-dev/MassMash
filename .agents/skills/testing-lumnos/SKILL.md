# Testing LUMNOS EduAI Companion

## Local Development Setup

### Backend
```bash
cd eduai-companion/eduai-backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Uses SQLite locally (`app.db`), PostgreSQL (Supabase) in production
- Non-fatal warnings for missing `psutil` and `pytz` are expected locally
- Backend .env contains all API keys (Groq, Clerk, Stripe, Tavily, etc.)
- `LUMNOS_DEV_MODE=1` enables dev bypass for authentication

### Frontend
```bash
cd eduai-companion/eduai-frontend
# Set VITE_API_URL in .env.local to point to local backend
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```
- Default port is 5173 (falls back to 5174 if in use)
- `VITE_DEV_BYPASS=true` in `.env` enables dev bypass login (skips Clerk OAuth)
- With dev bypass, the app auto-logs in as a test user (user_id 1001)

## Authentication

### Local Dev
- `VITE_DEV_BYPASS=true` creates a dev token that the backend accepts
- Clerk JWT tokens may expire quickly in dev mode — some secondary endpoints return 401, which is expected
- Core endpoints (`/api/progress`, `/api/gamification/profile`, `/api/gamification/add-xp`, `/api/shop/items`, `/api/chat/stream`) work with dev tokens
- Secondary endpoints (`/api/quests/today`, `/api/events/active`, `/api/quiz/blind-spots`, `/api/stats/weekly`) may fail with 401 in dev mode

### Production / Preview
- Uses Clerk OAuth (publishable key in `.env`)
- Preview URLs on Vercel require Clerk sign-in
- No VITE_DEV_BYPASS on production/preview builds

## Key Testing Flows

### Dashboard Real Data Flow
1. Navigate to Chat page (default page)
2. Send a chat message (type in textarea at bottom, press Enter)
3. After AI responds, `gamificationApi.addXp(5, "chat")` is called automatically
4. Navigate to Dashboard via sidebar
5. Verify: XP increased, Streak started, Chat count incremented, Quests updated

### Key API Endpoints to Verify
- `POST /api/chat/stream` — Chat streaming (returns 200)
- `POST /api/gamification/add-xp?xp=5&activity=chat` — XP awarding (returns 200)
- `GET /api/progress` — Learning progress with chat/quiz counts
- `GET /api/gamification/profile` — XP, streak, level data
- `POST /api/ws/ticket` — WebSocket ticket issuance
- `WebSocket /api/notifications/ws/notifications/{user_id}?ticket={ticket}` — Notification bell

### WebSocket / Notification Bell
- NotificationBell component in GlobalHeader (always visible when authenticated)
- Uses ticket-based auth: frontend gets ticket via `POST /api/ws/ticket`, then connects WebSocket with ticket
- Tickets are DB-backed (ws_tickets table) for multi-instance production safety
- BotProtectionMiddleware skips WebSocket paths (`/ws/`, `/api/notifications/ws/`, `/api/multiplayer/ws/`)
- Check backend logs for `WebSocket ... [accepted]` and `connection open` to verify

## App Navigation
- Sidebar opens via hamburger button (top-left)
- Pages: Dashboard, KI-Tutor (Chat), Quiz, IQ-Test, Lernpfad, Wissensdatenbank, Abitur-Simulation, Internet-Recherche, Gamification, Gruppen-Chats, Turniere, Karteikarten
- Default page is "chat" (KI-Tutor)
- GlobalHeader shows: streak count, XP, notification bell, theme toggles

## Common Gotchas
- Port 5173 may be in use from previous sessions — Vite auto-falls back to 5174
- Port 8000 may be in use — kill old processes with `kill <pid>` before restarting
- Clerk JWT tokens expire quickly in local dev — secondary endpoint 401s are expected
- Dashboard shows "4/7 API calls failed" in dev mode due to JWT expiration — core data still loads correctly
- The `sqlite3` CLI tool may not be installed — read database.py schema directly instead
- Some recordings may not capture terminal output — only browser GUI is recorded

## Devin Secrets Needed
- `GROQ_API_KEY` — For LLM chat responses (stored in backend .env)
- `GITHUB_USERNAME` / `GITHUB_PASSWORD` — For git operations
