# Testing Clerk Auth Flow

## Overview
The LUMNOS app uses Clerk for authentication (GitHub, Google, Apple OAuth). The frontend runs on Vercel, the backend on Render. Testing auth requires understanding that these deploy independently.

## Architecture
- **Frontend (Vercel)**: Clerk SDK handles OAuth, stores session. Preview deployments are auto-created per PR branch.
- **Backend (Render)**: Verifies Clerk JWTs via JWKS endpoint. Only updates when `main` branch is deployed.
- **Clerk tokens**: RS256 JWTs that expire every ~60 seconds. The frontend must get fresh tokens from Clerk SDK before each API call.

## Key Files
- `eduai-frontend/src/App.tsx` — Clerk → AuthStore sync effect (registers getToken, syncs on sign-in)
- `eduai-frontend/src/stores/authStore.ts` — `loadUser` (handles token refresh), `loginWithClerk` (sets fallback user)
- `eduai-frontend/src/services/api.ts` — `registerClerkGetToken`, `getFreshClerkToken`, `isClerkToken` (RS256 detection)
- `eduai-backend/app/core/auth.py` — `get_current_user` (Clerk JWT verification via JWKS)
- `eduai-backend/app/core/clerk.py` — `fetch_clerk_user` (calls Clerk Backend API for user details)
- `eduai-backend/app/core/security.py` — Rate limiting with auth multiplier

## Known Race Condition
On page load after OAuth redirect, `loadUser` and the Clerk sync effect can race:
1. `loadUser` finds a stale Clerk token in localStorage
2. For local JWTs, it would try `refreshAccessToken()` which fails for Clerk tokens
3. Fix: `loadUser` detects RS256 tokens via `isClerkToken()` and skips local refresh
4. Fix: Clerk sync effect includes `isAuthenticated` in deps so it re-fires after loadUser

## Testing Steps

### Frontend-Only Testing (Vercel Preview)
1. Navigate to the Vercel preview URL from the PR
2. Clear localStorage (`localStorage.clear()`) to start fresh
3. Verify Clerk login widget renders (Apple, GitHub, Google buttons)
4. Click GitHub OAuth → authorize → redirected back
5. **Check**: App should show dashboard (not blank login page)
6. **Check console**: 401 errors from backend are expected if backend hasn't been updated
7. **Check**: No infinite redirect loops or JS crashes

### Full E2E Testing (after backend deploy)
1. Merge the auth PR into `main` and wait for Render to redeploy
2. Ensure `CLERK_SECRET_KEY` is set in Render env vars
3. Log in via Clerk on production (`https://mass-mash.vercel.app`)
4. Open DevTools Network tab
5. **Check**: `/api/auth/me` returns 200 with user data
6. **Check**: Chat messages send and receive (SSE streaming)
7. **Check**: Dashboard shows real stats (not all 0s)
8. **Check**: No 401/429 errors in console

## Devin Secrets Needed
- `GITHUB_USERNAME` — For GitHub OAuth login during testing
- `GITHUB_PASSWORD` — For GitHub OAuth login during testing

## Common Issues
- **Blank login page after OAuth**: Race condition between `loadUser` and Clerk sync. Check if `isClerkToken` detection is working.
- **Clerk widget says 'user already signed in' but app shows login**: The Clerk sync effect might not be re-firing. Check dependency array includes `isAuthenticated`.
- **429 on /api/auth/refresh**: Old backend rate limiting. The auth fix relaxes this for authenticated users.
- **Clerk development keys warning**: Normal for dev/preview. Production should use production Clerk keys.
- **Backend and frontend deploy independently**: Vercel previews update per-PR, but Render only deploys from `main`. Frontend auth changes may work on preview but backend needs separate merge+deploy.
