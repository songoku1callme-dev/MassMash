# Testing LUMNOS Frontend

## Overview
LUMNOS is a full-stack AI tutoring platform for German students. The frontend is a React + Vite app with Clerk authentication, Zustand state management, and a polling-based notification system.

## Devin Secrets Needed
- `VITE_CLERK_PUBLISHABLE_KEY` — Clerk publishable key (pk_test_* for dev, pk_live_* for prod)
- No other secrets needed for frontend-only testing

## Local Dev Server Setup
1. `cd eduai-companion/eduai-frontend`
2. `npm install`
3. `npm run dev` — starts Vite on http://localhost:5173

## Auth Bypass for Testing
The app requires authentication. To bypass without a running backend:
1. Open browser console on `http://localhost:5173`
2. Run:
   ```js
   localStorage.setItem('lumnos_token', 'dev-max-token-lumnos');
   localStorage.setItem('lumnos_user', JSON.stringify({
     id: 999, email: 'admin@lumnos.de', username: 'TestAdmin',
     full_name: 'Test Admin', school_grade: '12', school_type: 'Gymnasium',
     preferred_language: 'de', is_pro: true, subscription_tier: 'max',
     ki_personality_id: 1, ki_personality_name: 'Mentor', avatar_url: '',
     auth_provider: 'dev', created_at: new Date().toISOString()
   }));
   location.reload();
   ```
3. The app will load with a dev user session (authStore.ts recognizes `dev-max-token-lumnos`)

## Key UI Navigation
- **Sidebar** (left) contains all page links: Dashboard, KI-Tutor, Quiz, etc.
- **GlobalHeader** (top) shows user name, NotificationBell, and theme toggles
- Default page after auth is **Chat** (KI-Tutor)
- Page routing is state-based via `currentPage` in App.tsx (not URL-based)

## Testing NotificationBell (Polling)
- The NotificationBell is rendered in `GlobalHeader.tsx`
- It uses a **polling-first** architecture: GET `/api/notifications/bell` every 30s
- WebSocket is attempted as an optional upgrade but fails silently
- To verify: Check browser console for absence of WebSocket 403 errors
- The `/api/ws/ticket` endpoint may return 500 without a backend — this is expected and handled gracefully

## Testing Dashboard (React Key Warnings)
- Navigate to Dashboard via sidebar
- The Quests section uses `key={quest.id || \`quest-${i}\`}` for fallback keys
- Check browser console for absence of "Each child in a list should have a unique 'key' prop" warnings
- Dashboard renders stats cards, quests, KI-Tutor card, and Lernstatistik chart

## Common Console Errors (Expected Without Backend)
- `500 Internal Server Error` on `/api/auth/refresh`, `/api/chat/sessions`, `/api/admin/check` — expected when no backend is running
- `404` on Clerk avatar images — sometimes happens with dev keys
- `Clerk: Clerk has been loaded with development keys` — expected warning in dev mode

## Backend /health Endpoint
- `GET /health` returns `{"status": "ok", "version": "..."}`
- This endpoint is excluded from BotProtectionMiddleware (security.py)
- Can be tested with `curl https://lumnos-backend.onrender.com/health` after deployment

## Lint & Build
- `npm run lint` — ESLint check
- `npm run build` — Vite production build
- `npm run test` — Vitest unit tests
