# Testing LUMNOS Frontend

## Overview
LUMNOS is a German AI tutoring app (React + Vite) with Clerk authentication, deployed on Vercel (frontend) and Render (backend).

## Devin Secrets Needed
- None required for basic frontend testing (dev-token bypass available)
- For production backend testing: backend may need Render access

## Authentication for Testing

The app uses Clerk for authentication. To bypass Clerk login in the browser:

1. Navigate to the preview/production URL
2. Open browser console and run:
```js
localStorage.setItem('lumnos_token', 'dev-max-token-lumnos');
localStorage.setItem('lumnos_access_token', 'dev-max-token-lumnos');
localStorage.setItem('lumnos_user', JSON.stringify({
  id: 999, email: 'admin@lumnos.de', username: 'TestAdmin',
  full_name: 'Test Admin', school_grade: '12', school_type: 'Gymnasium',
  preferred_language: 'de', is_pro: true, subscription_tier: 'max',
  ki_personality_id: 1, ki_personality_name: 'Mentor', avatar_url: '',
  auth_provider: 'dev', created_at: new Date().toISOString()
}));
window.location.reload();
```
3. This creates a dev user with Max subscription tier and full access

## Navigation

The app is a SPA — direct URL paths (e.g. `/dashboard`) return 404 on Vercel preview. Always navigate via:
- Root URL loads AuthPage or ChatPage (if authenticated)
- Use the **sidebar** to navigate between pages (Dashboard, KI-Tutor, Quiz, Pricing, etc.)
- Sidebar items at the bottom require scrolling: Abo & Preise, Einstellungen, Admin-Panel

## Key Pages to Test

### Dashboard (`Dashboard` in sidebar)
- Shows greeting, 4 stat cards (Streak, XP, Fächer, Rang)
- Tägliche Quests section with fallback quests when API fails
- 7-Tage XP Chart with fallback random data
- Quick Actions: Chat starten, Quiz spielen, Karteikarten, Abitur-Sim
- Bottom tiles: Tages-Quiz, Scanner, Turnier, Belohnungs-Shop, Gamification
- API failures are logged to console as `[Dashboard] API xyz failed`

### ChatPage (`KI-Tutor` in sidebar)
- Welcome message: "Was möchtest du wissen?"
- Example questions with correct German umlauts
- Subject selector, personality selector, language toggle
- Textarea placeholder changes based on mode (tutor/ELI5/normal)

### PricingPage (`Abo & Preise` in sidebar — scroll down in sidebar to find it)
- 4 pricing tiers: Kostenlos, Pro, Max, Eltern
- Feature lists with German text (Fächer, über, etc.)

## Common Issues

- **Dashboard appears empty**: API calls may fail silently. Check browser console for `[Dashboard]` warnings. The Dashboard should still render all sections with fallback/demo data.
- **Unicode escapes visible**: If you see `\u00e4` instead of `ä`, the source files need UTF-8 character replacement.
- **Cookie banner blocks interaction**: Click "Alle akzeptieren" to dismiss. If it doesn't work via devinid, try coordinates.
- **Vercel preview 404 on direct paths**: Use root URL + sidebar navigation instead of direct paths like `/dashboard`.
- **Backend cold start**: Render free-tier may take 30+ seconds to wake up. The app has a keep-alive ping every 10 minutes.

## Backend Health Check

- `/health` endpoint should return 200 OK with `{"status":"ok"}`
- If it returns 403, check that `/health` is in `SKIP_AUTH_PATHS` in `BotProtectionMiddleware` (security.py)
- Test with: `curl https://lumnos-backend.onrender.com/health`
