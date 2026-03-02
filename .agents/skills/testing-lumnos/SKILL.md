# Testing LUMNOS EduAI Companion

## Overview
LUMNOS is an AI tutoring app with a Python/FastAPI backend and React/Vite frontend. Testing requires running both locally.

## Devin Secrets Needed
- `GROQ_API_KEY` — for KI chat responses
- `STRIPE_SECRET_KEY` — for payment features
- `TAVILY_API_KEY` — for internet research
- `RESEND_API_KEY` — for email features
- `CLERK_SECRET_KEY` — for auth (if Clerk is enabled)
- `VITE_CLERK_PUBLISHABLE_KEY` — for frontend Clerk auth

## Local Setup

### Backend
```bash
cd eduai-companion/eduai-backend
export LUMNOS_DEV_MODE=1  # CRITICAL: enables CORS for all origins
export GROQ_API_KEY=<secret>
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd eduai-companion/eduai-frontend
# Create .env.local to override production API URL
echo 'VITE_API_URL=http://localhost:8000' > .env.local
npx vite --host 0.0.0.0 --port 5175
```

**Important**: Vite `.env` file contains the production URL. You MUST create `.env.local` with `VITE_API_URL=http://localhost:8000` to override it. Vite loads `.env.local` with higher precedence than `.env`.

## Common Issues

### CORS Errors
- **Symptom**: Browser console shows "Access to fetch blocked by CORS policy"
- **Fix**: Restart backend with `export LUMNOS_DEV_MODE=1` before starting uvicorn
- The backend's CORS middleware checks this env var to allow all origins

### Frontend Pointing to Production API
- **Symptom**: Network requests go to `https://app-kbhrgvhm.fly.dev` instead of localhost
- **Fix**: Create `.env.local` with `VITE_API_URL=http://localhost:8000` and restart frontend
- Command-line env vars do NOT override `.env` files in Vite

### Auth / Login Issues
- Register a test user via API: `curl -X POST http://localhost:8000/api/auth/register -H 'Content-Type: application/json' -d '{"username":"testuser3","email":"test3@lumnos.de","password":"test123"}'`
- If login UI doesn't work, set tokens directly via browser console:
  ```javascript
  // After getting token from /api/auth/login via curl
  localStorage.setItem('lumnos_token', '<access_token>');
  localStorage.setItem('lumnos_refresh_token', '<refresh_token>');
  window.location.reload();
  ```
- Token keys: `lumnos_token` and `lumnos_refresh_token`

### Session Expired Message
- Clear all storage: `localStorage.clear(); sessionStorage.clear(); document.cookie.split(';').forEach(c => document.cookie = c.trim().split('=')[0] + '=;expires=Thu, 01 Jan 1970');`
- Then reload the page

## App Navigation
- The app uses **internal state-based routing** (not URL-based)
- `currentPage` state in App.tsx controls which page renders
- To navigate programmatically: `window.dispatchEvent(new CustomEvent('navigate', { detail: 'chat' }));`
- Pages: dashboard, chat, quiz, iq-test, lernpfad, etc.

## Testing Chat + Karteikarten
1. Navigate to Chat page (click KI-Tutor in sidebar or use JS navigation)
2. The input field may not respond to browser tool clicks — use JavaScript to set value:
   ```javascript
   const input = document.querySelector('input[placeholder="Stelle eine Frage..."]');
   const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
   setter.call(input, 'Was ist der Satz des Pythagoras?');
   input.dispatchEvent(new Event('input', { bubbles: true }));
   ```
3. Submit via form: `document.querySelector('form').requestSubmit();`
4. Wait ~15 seconds for Groq API response
5. Verify: Zusammenfassung (cyan italic text), "3 Karteikarten anzeigen" button (amber)
6. Click button to expand cards — may need JavaScript click
7. Click a card to flip it — shows "Antwort" with green styling

## Testing via API (Alternative)
If browser interactions are difficult, test the chat API directly:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"message":"Was ist der Satz des Pythagoras?","subject":"Mathematik"}'
```
Response should include `karteikarten` array (3 items) and `zusammenfassung` string.

## Admin Emails (permanent Max tier)
- ahmadalkhalaf2019@gmail.com
- songoku1callme@gmail.com
- 261al3nzi261@gmail.com
- 261g2g261@gmail.com

## Key URLs
- **Fly.io Backend**: https://app-kbhrgvhm.fly.dev
- **Vercel Preview**: Check PR for latest preview URL (may require SSO)
- **Local Backend**: http://localhost:8000
- **Local Frontend**: http://localhost:5175

## Tips
- Browser tool clicks on React components may be blocked — use JavaScript `element.click()` as fallback
- For form submissions, `form.requestSubmit()` works better than clicking submit buttons
- Always check browser console for errors after actions
- The LumnosOrb component renders as a ✦ symbol with animation effects
- German umlauts (ä, ö, ü) must be used everywhere — never ae, oe, ue
