# Testing LUMNOS Chat & KI-Modi

How to E2E test the LUMNOS KI-Tutor chat with all 3 response modes (Fast, Standard, Deep Thinking).

## Devin Secrets Needed
- `GROQ_API_KEY` — Required for backend AI responses

## Setup

### Backend
```bash
cd eduai-companion/eduai-backend
set -a && source .env && set +a
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Confirm: `ss -tlnp | grep 8000` should show python listening.

### Frontend (CRITICAL: avoid CORS)
```bash
cd eduai-companion/eduai-frontend
# Do NOT set VITE_API_URL! Leave it empty in .env
npx vite --host 0.0.0.0 --port 5173
```
**Why no VITE_API_URL?** The Vite dev server has a proxy configured in `vite.config.ts` that routes `/api` requests to `http://127.0.0.1:8000`. If you set `VITE_API_URL=http://localhost:8000`, the frontend makes direct cross-origin requests which get blocked by CORS. Leaving it empty lets Vite's proxy handle routing seamlessly.

If port 5173 is busy, Vite auto-assigns 5174/5175 — the proxy still works on any port.

### Authentication (Dev Bypass)
In browser console:
```js
localStorage.setItem('lumnos_token', 'dev-max-token-lumnos');
localStorage.setItem('lumnos_refresh_token', 'dev-refresh-token');
location.reload();
```
This creates a TestAdmin user with Max subscription tier.

## Testing the 3 KI-Modi

All 3 mode buttons appear above the chat input area:
- **Fast** (yellow, lightning bolt) — Uses 8b-instant model, ~200 tokens, <3 sec
- **Standard** (blue, sparkles) — Uses 70b-versatile model, balanced response
- **Deep** (purple, brain) — Two-pass verification: generate -> self-check -> improve, 15-30 sec

### Test Procedure
1. Navigate to the chat page (KI-Tutor in sidebar)
2. Click a mode button to select it (it highlights with color)
3. Type a test question, e.g. "Was ist die Ableitung von sin(x)?"
4. Click send arrow
5. Verify:
   - **Fast**: Quick response, short, mentions cos(x)
   - **Standard**: Full explanation with LaTeX formulas, "KI-Geprüft" badge
   - **Deep**: Shows "Deep Thinking läuft..." animation, then detailed response with "Denkprozess anzeigen" expandable section and "KI-Geprüft" badge
6. Click "Neuer Chat" between tests to start fresh

## Common Issues

### CORS Errors
Symptom: Browser console shows "Access to fetch blocked by CORS policy"
Fix: Restart frontend WITHOUT `VITE_API_URL` set. Check `.env` has `VITE_API_URL=` (empty).

### Port Conflicts
If port 5173 is occupied: `fuser -k 5173/tcp` to kill the process, then restart.
Or just use the auto-assigned port (5174, 5175, etc.).

### Frontend Process Management
Use separate shell sessions for backend and frontend. Running frontend with `nohup` in background can work but monitor via log file: `nohup npx vite --host 0.0.0.0 --port 5173 > /tmp/frontend.log 2>&1 &`

### Groq Rate Limits
Groq free tier has daily token limits. If responses fail with rate limit errors, wait or use a different API key.
