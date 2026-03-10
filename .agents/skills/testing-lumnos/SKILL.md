# Testing LUMNOS EduAI App

## Overview
LUMNOS is a German-language AI tutoring platform with a React frontend (Vercel) and FastAPI backend (Render free tier).

## Devin Secrets Needed
- `GITHUB_OAUTH_PASSWORD` — GitHub password for songoku1callme@gmail.com (used for Clerk OAuth login)
- Google OAuth is blocked by iPhone 2FA; use GitHub OAuth as the alternative login method

## Architecture
- **Frontend:** Vite + React, deployed on Vercel. Preview URLs follow pattern: `mass-mash-git-{branch-slug}-songoku1callme-devs-projects.vercel.app`
- **Backend:** FastAPI on Render free tier at `https://lumnos-backend.onrender.com`
- **Auth:** Clerk (development keys). OAuth providers: Google (blocked by 2FA), GitHub (working)
- **Owner system:** 5 whitelisted emails loaded from `VITE_OWNER_EMAILS` env var in Vercel (build-time)

## Login Flow
1. Navigate to the app URL
2. Clerk login widget appears with loading bar
3. Click "Weiter mit GitHub" (Continue with GitHub) button
4. GitHub OAuth redirects to github.com for authorization
5. After authorization, redirects back to app
6. App shows "KI-Gehirn wird geweckt..." loading screen while backend wakes up (30-60s on Render free tier)
7. Once backend responds, app fully loads to KI-Tutor (ChatPage)

**Important:** If Clerk loading bar appears stuck, wait 10-15 seconds. If Google OAuth prompts for iPhone 2FA verification, cancel and use GitHub OAuth instead.

## Owner UI Verification Checklist
When logged in as an owner email (e.g., songoku1callme@gmail.com):

### Sidebar (always visible)
- Bottom-left: Green emerald star icon + "Owner" label (not "Max" or "Pro")
- Scroll down to see: "Admin-Panel" and "Forschungs-Zentrum" links

### Dashboard
- NO "Pro upgraden" button in the header area (top-right)
- NO upgrade banner at the bottom of the page
- Time display shows local browser time

### PricingPage ("Abo & Preise")
- Yellow banner at top: "Du bist Owner-Mitglied!" with crown icon and star
- All 4 pricing cards still visible (Kostenlos, Pro, Max, Eltern)

### ChatPage ("KI-Tutor")
- NO "Pro · 4,99\u20ac" upgrade button in the toolbar
- Purple gradient "Owner" tier badge visible in the toolbar

## Backend Health Checks
```bash
# These should return 200 OK (skip auth):
curl https://lumnos-backend.onrender.com/healthz
curl https://lumnos-backend.onrender.com/api/ping

# This needs /health in SKIP_AUTH_PATHS (after PR merge):
curl https://lumnos-backend.onrender.com/health
```

## Common Issues

### Render Free Tier Cold-Start
- Backend sleeps after inactivity, takes 30-60s to wake up
- App shows "KI-Gehirn wird geweckt..." loading screen during cold-start
- Keep-Alive ping (`/healthz` every 10 min) mitigates this
- If backend is in "Failed service" state on Render dashboard, use "Clear build cache & deploy"

### Rate Limiting (429)
- Backend returns 429 on rapid repeated requests
- Wait a few seconds between page reloads during testing
- Console errors like "Zu viele Anfragen" are from rate limiting

### Vercel Preview Deployment Caching
- After pushing new commits, Vercel preview URL may serve old build for 1-2 minutes
- Use hard refresh (Ctrl+Shift+R) to pick up new deployments
- Check Vercel deployment timestamp in PR comments to confirm new build

### Unicode/Umlaut Issues
- Some Dashboard tiles show `\u00e4` instead of `\u00e4` (pre-existing cosmetic issue)
- Not related to Owner UI fixes

### Clerk Development Keys Warning
- Console warning about "development keys" is expected in preview/staging environments
- Does not affect functionality

## Environment Variables (Vercel)
- `VITE_OWNER_EMAILS`: Comma-separated list of 5 owner emails (build-time)
- `VITE_API_URL`: Backend URL (`https://lumnos-backend.onrender.com`)
- `VITE_CLERK_PUBLISHABLE_KEY`: Clerk publishable key (also in committed .env)

## Render Backend
- Deploy branch: `main`
- Service ID: `srv-d6m774vtskes73dnmhu0`
- Access via Render dashboard (login with GitHub OAuth as songoku1callme@gmail.com)
- After merging PRs to main, Render auto-deploys (or trigger manual deploy from dashboard)
