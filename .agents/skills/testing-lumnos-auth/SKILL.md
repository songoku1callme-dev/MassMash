# LUMNOS Auth & E2E Testing

## Overview
LUMNOS is a German AI tutoring app (EduAI Companion) with a React frontend (Vite) deployed on Vercel and a FastAPI backend deployed on Render free tier. Authentication uses Clerk OAuth (GitHub, Google, Apple) with RS256 JWT tokens.

## Devin Secrets Needed
- `GITHUB_ACCOUNT` — GitHub account credentials for OAuth login testing
- Clerk dashboard access may be needed to verify user creation

## Architecture
- **Frontend**: React + Vite, deployed on Vercel (`mass-mash.vercel.app`)
- **Backend**: FastAPI + SQLite, deployed on Render (`lumnos-backend.onrender.com`)
- **Auth**: Clerk OAuth (development instance at `native-orca-10.clerk.accounts.dev`)
- **Dual JWT**: Clerk tokens (RS256, ~60s expiry) + built-in JWT (HS256, 30min expiry)

## Testing Clerk OAuth Login

### Prerequisites
1. Vercel preview URL from PR (check `git_view_pr` for Vercel bot comment)
2. GitHub account that can authorize Clerk OAuth
3. Backend must be running (`curl https://lumnos-backend.onrender.com/health` should return 200)

### Steps
1. Navigate to the Vercel preview URL
2. Wait for Clerk SignIn widget to render (Apple/GitHub/Google buttons)
3. Click GitHub OAuth button
4. Authorize Clerk on GitHub's OAuth page
5. After redirect, verify dashboard loads (NOT stuck on "Laden..." loading screen)
6. Check console for errors — should see NO 429 on `/api/auth/refresh`
7. Verify sidebar shows user name + "Owner" badge (if applicable)

### Common Issues

#### Clerk Dev Browser JWT Error
- **Symptom**: `Error: ClerkJS: Missing dev browser jwt` in console, SignIn widget disappears
- **Cause**: Clearing localStorage/cookies also clears Clerk's dev browser JWT cookie
- **Fix**: Don't clear cookies before testing. If already cleared, just reload the page — Clerk will re-establish the session
- **Note**: This only affects Clerk development instances, not production

#### 429 Rate Limit Loop on `/api/auth/refresh`
- **Symptom**: App stuck on "Laden..." (loading) after OAuth login, 429 errors in console
- **Cause**: `useAuthRefresh` hook was calling `/api/auth/refresh` for Clerk tokens (RS256), which only handles built-in JWT (HS256). Clerk tokens expire every ~60s, always triggering the 120s "expiring soon" check
- **Fix**: PR #76 added `isClerkToken()` guard to skip Clerk tokens in `useAuthRefresh`
- **If it recurs**: Check `useAuthRefresh.ts` — make sure `isClerkToken(token)` early return is present

#### Render Free Tier Cold Start
- **Symptom**: Backend returns 503/502 errors, `/health` fails
- **Cause**: Render free tier puts services to sleep after inactivity. Docker builds take 15-20+ minutes
- **Fix**: Wait for `/health` to return 200 before testing. The app has a keep-alive ping every 10 minutes
- **Manual deploy**: Render free tier does NOT auto-deploy on GitHub merge. Must use Render dashboard > Manual Deploy

#### Clerk Development Keys Warning
- **Symptom**: Console warning about "development keys" and "strict usage limits"
- **Impact**: This is expected for development Clerk instances. Does not affect functionality but means the Clerk instance has rate limits
- **Note**: For production, the Clerk instance should be upgraded to production keys

## Testing Chat/Quiz Features
1. After successful login, navigate to KI-Tutor (Chat) page
2. Type a message and send — verify SSE streaming works
3. Navigate to Quiz page — verify it loads
4. If backend is newly deployed, first API call may be slow (cold start)

## Key Files
- `eduai-frontend/src/hooks/useAuthRefresh.ts` — Token refresh hook (must skip Clerk tokens)
- `eduai-frontend/src/services/api.ts` — API layer with Clerk token detection (`isClerkToken()`)
- `eduai-frontend/src/stores/authStore.ts` — Auth state management (`loginWithClerk`, `loadUser`)
- `eduai-frontend/src/App.tsx` — Clerk sync effect, `useAuthRefresh` mount point
- `eduai-backend/app/core/auth.py` — Backend dual auth (Clerk RS256 + built-in HS256)
- `eduai-backend/app/core/clerk.py` — Clerk JWKS verification + user fetch
