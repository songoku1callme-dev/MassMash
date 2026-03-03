# Testing LUMNOS Authentication System

## Overview
LUMNOS has 3 auth methods: Dev Bypass, Google OAuth (Clerk), and Email OTP. This skill covers how to test each locally.

## Prerequisites

### Backend Setup
```bash
cd eduai-companion/eduai-backend
set -a && source .env && set +a
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Required env vars in backend `.env`:
- `LUMNOS_DEV_MODE=1` — enables dev bypass endpoint and returns OTP codes in API responses
- `SECRET_KEY` — for JWT signing (auto-generated if missing)
- `RESEND_API_KEY` — for sending OTP emails (optional in dev, codes returned in response)

### Frontend Setup
```bash
cd eduai-companion/eduai-frontend
npx vite --port 5175 --host
```

Required env vars in frontend `.env`:
- `VITE_DEV_BYPASS=true` — enables auto-login on page load
- `VITE_CLERK_PUBLISHABLE_KEY` — for Google OAuth
- `VITE_API_URL` — leave empty when using Vite proxy (recommended)

### CRITICAL: Vite Proxy
The `vite.config.ts` MUST have a proxy configured to forward `/api` requests to the backend:
```ts
server: {
  proxy: {
    "/api": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
  },
},
```
Without this proxy, the frontend's fetch calls to `/api/auth/dev-bypass` will hit the Vite dev server instead of the backend, and the dev bypass will silently fail (falling through to the landing page).

## Test Flow 1: Dev Bypass (FIX 1)
1. Clear localStorage: `localStorage.clear()` in browser console
2. Reload the page
3. Expected: App auto-authenticates via `/api/auth/dev-bypass` and lands on KI-Tutor/Chat page
4. Verify: Sidebar shows username, tier badge (e.g. "Max"), and grade

**Troubleshooting**: If landing page shows instead of auto-login:
- Check that `VITE_DEV_BYPASS=true` is in frontend `.env`
- Check that Vite proxy is configured (see above)
- Check that backend has `LUMNOS_DEV_MODE=1` in `.env`
- Check backend logs for errors on `/api/auth/dev-bypass`

## Test Flow 2: Email OTP (FIX 3)
Test via browser console (no UI form needed for API verification):

### Send OTP Code
```javascript
fetch('/api/auth/send-magic-link', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'test@lumnos.de'})
}).then(r => r.json()).then(d => console.log('RESULT:', JSON.stringify(d)))
```
Expected: `{"success":true, "dev_code":"XXXXXX"}` (dev_code only when LUMNOS_DEV_MODE=1)

### Verify OTP Code
```javascript
fetch('/api/auth/verify-code', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'test@lumnos.de', code: 'XXXXXX'})
}).then(r => r.json()).then(d => console.log('RESULT:', JSON.stringify(d)))
```
Expected: `{"access_token":"...", "refresh_token":"...", "user":{...}, "is_new_user":true}`

### Test Wrong Code (Brute-Force Protection)
Send verify-code with unknown email:
```javascript
fetch('/api/auth/verify-code', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'unknown@test.de', code: '000000'})
}).then(r => r.json()).then(d => console.log('RESULT:', JSON.stringify(d)))
```
Expected: `{"detail":"Kein Code fuer diese E-Mail gefunden."}`

## Test Flow 3: Clerk Redirect URL (FIX 2)
Verify in browser console that the Clerk redirect URL uses `window.location.origin` dynamically:
```javascript
const key = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const body = key.replace('pk_test_', '').replace(/\$.*/, '');
const redirect = window.location.origin + '/dashboard';
console.log(`https://${body}.clerk.accounts.dev/sign-in?redirect_url=${encodeURIComponent(redirect)}`);
```
Expected: `redirect_url` should contain current domain (e.g. `localhost:5175` or tunnel domain), NOT hardcoded.

## Devin Secrets Needed
- `RESEND_API_KEY` — for sending real OTP emails (optional for dev testing)
- `GROQ_API_KEY` — for AI chat functionality (not needed for auth testing)
