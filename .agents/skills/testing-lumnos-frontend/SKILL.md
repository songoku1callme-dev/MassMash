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
1. Open browser console on the app URL (localhost or Vercel preview)
2. Run:
   ```js
   localStorage.setItem('lumnos_token', 'dev-max-token-lumnos');
   localStorage.setItem('lumnos_user', JSON.stringify({
     id: 999, email: 'songoku1callme@gmail.com', username: 'Owner',
     full_name: 'Owner Test', school_grade: '12', school_type: 'Gymnasium',
     preferred_language: 'de', is_pro: true, subscription_tier: 'max',
     ki_personality_id: 1, ki_personality_name: 'Mentor', avatar_url: '',
     auth_provider: 'dev', created_at: new Date().toISOString()
   }));
   ```
3. Reload the page — the app will load with auth (authStore.ts recognizes `dev-max-token-lumnos`)
4. To test as a **non-owner** user, use any email NOT in the owner list (e.g., `test@example.com`)

## Owner Email Testing
Owner emails get special privileges — `is_pro: true`, `subscription_tier: "max"`, and bypass all feature gates.

### Owner emails are defined in:
- `eduai-frontend/src/utils/ownerEmails.ts` — canonical frontend list
- `eduai-backend/app/routes/auth.py` — backend OWNER_EMAILS
- `eduai-backend/app/routes/admin.py` — backend admin check
- `eduai-backend/app/routes/chat.py` — backend chat overrides
- `eduai-backend/app/core/database.py` — database seed

### What to verify for owner emails:
| Page | Expected Behavior |
|------|-------------------|
| Sidebar | Green star icon + "Owner" label (bottom-left) |
| ChatPage | Green "Owner" badge in header area, no upgrade CTA |
| DashboardPage | No upgrade banner, personalized "Guten Morgen, Owner!" greeting |
| Admin-Panel | Full access (sidebar link visible, page loads with stats) |
| PricingPage | Green banner "Du bist Owner-Mitglied!", Max plan shows "Aktiv" |
| Forschungs-Zentrum | Accessible via sidebar (admin-only) |

### Important: Sidebar has a separate hardcoded ADMIN_EMAILS list
- `Sidebar.tsx` has its own `ADMIN_EMAILS` array for local admin fallback
- This is separate from `ownerEmails.ts` — the API check (`adminApi.check()`) takes precedence
- If updating owner emails, also check if `Sidebar.tsx` ADMIN_EMAILS needs updating

## Vercel Preview Testing
- PRs automatically get Vercel preview deployments
- Preview URL format: `https://mass-mash-git-{branch}-songoku1callme-devs-projects.vercel.app`
- The auth bypass works on preview URLs — just inject localStorage before reload
- Cookie consent dialog may appear on first load — click "Alle akzeptieren" or wait for auto-dismiss
- Backend API calls will fail on preview (expected) since the preview only deploys frontend

## Key UI Navigation
- **Sidebar** (left) contains all page links: Dashboard, KI-Tutor, Quiz, etc.
- **GlobalHeader** (top) shows user name, NotificationBell, and theme toggles
- Default page after auth is **Chat** (KI-Tutor)
- Page routing is state-based via `currentPage` in App.tsx (not URL-based)
- Admin-Panel and Forschungs-Zentrum are at the bottom of the sidebar — scroll down to find them

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
- This endpoint is in SKIP_AUTH_PATHS (security.py) — bypasses all auth and rate limiting
- Can be tested with `curl https://lumnos-backend.onrender.com/health` after deployment
- If /health returns 403, check that SKIP_AUTH_PATHS includes "/health" in security.py

## Lint & Build
- `npm run lint` — ESLint check
- `npm run build` — Vite production build
- `npm run test` — Vitest unit tests
