# LUMNOS Deployment Guide

## Kostenloser Stack (24/7, kein Kreditkarte)

| Service | Anbieter | Kosten | URL |
|---------|----------|--------|-----|
| Frontend | Vercel | Kostenlos | vercel.com |
| Backend | Koyeb | Kostenlos (Free Tier, kein Sleep) | koyeb.com |
| Datenbank | Supabase | Kostenlos (500MB PostgreSQL) | supabase.com |

## Setup Schritt fuer Schritt

### 1. Supabase (Datenbank)

1. Gehe zu [supabase.com](https://supabase.com) und erstelle ein kostenloses Projekt
2. Waehle **Frankfurt (eu-central-1)** als Region
3. Gehe zu **Settings > Database > Connection String > URI**
4. Kopiere die `postgresql://...` URL — das ist deine `DATABASE_URL`

### 2. Koyeb (Backend)

1. Gehe zu [koyeb.com](https://koyeb.com) und erstelle einen kostenlosen Account
2. Klicke **Create App > GitHub**
3. Verbinde dein GitHub Repository: `songoku1callme-dev/MassMash`
4. Setze den **Root Directory**: `eduai-companion/eduai-backend`
5. Wähle **Dockerfile** als Build-Methode
6. Setze die **Environment Variables** (siehe unten)
7. Klicke **Deploy**

### 3. Vercel (Frontend)

1. Gehe zu [vercel.com](https://vercel.com) und importiere das Repo
2. Setze **Root Directory**: `eduai-companion/eduai-frontend`
3. Setze die Environment Variables:
   - `VITE_API_URL` = `https://[dein-app-name].koyeb.app`
   - Alle weiteren `VITE_*` Variablen aus `.env.example`
4. Deploy

## Pflicht Environment Variables (Koyeb Backend)

```bash
# Sicherheit
SECRET_KEY=          # python -c "import secrets; print(secrets.token_urlsafe(64))"

# Datenbank (von Supabase)
DATABASE_URL=        # postgresql://... von Supabase Settings

# KI / API Keys
GROQ_API_KEY=        # console.groq.com (kostenlos)

# Bezahlung
STRIPE_SECRET_KEY=   # dashboard.stripe.com
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# Authentifizierung
CLERK_SECRET_KEY=    # dashboard.clerk.com

# Produktion
LUMNOS_DEV_MODE=0
BACKEND_URL=         # https://[dein-app-name].koyeb.app
PORT=8080
```

## Optionale Environment Variables

```bash
# KI Live-Wissen (AUFGABE 1)
TAVILY_API_KEY=      # tavily.com (1000 Requests/Monat kostenlos)

# E-Mail (Ghost Founder Engine)
RESEND_API_KEY=      # resend.com (100 Emails/Tag kostenlos)

# Monitoring
SENTRY_DSN=          # sentry.io (10k Events/Monat kostenlos)
POSTHOG_API_KEY=     # posthog.com (1M Events/Monat kostenlos)
```

## 512MB RAM Optimierung

Das Backend ist fuer 512MB RAM optimiert (Koyeb Free Tier):

- **Single Worker**: Nur 1 Uvicorn Worker (`--workers 1`)
- **Request Limit**: Auto-Restart nach 1000 Requests (`--limit-max-requests 1000`)
- **SQLite Cache**: `PRAGMA cache_size=-8000` (8MB, sicher fuer 512MB RAM)
- **Memory Env Vars**: `MALLOC_TRIM_THRESHOLD_=65536`, `PYTHONMALLOC=malloc`
- **Keep-Alive**: Self-Ping alle 10 Minuten verhindert Sleep

> **Hinweis**: Supabase PostgreSQL-Anbindung ist fuer einen zukuenftigen PR geplant.
> Aktuell nutzt das Backend SQLite lokal. Fuer Produktion mit Supabase muss
> `database.py` erweitert werden (dual-mode: SQLite lokal / PostgreSQL remote).

## APScheduler Jobs (25+ aktive Jobs)

Alle Jobs laufen automatisch im Hintergrund:
- **Taeglich**: Quests, Streaks, XP-Bonus, Motivation, Knowledge Update (Tavily)
- **Woechentlich**: Reports, Challenges, Shop-Rotation, Events
- **Monatlich**: Battle Pass, Turniere, Leaderboard Reset
- **Stuendlich**: Cleanup (Turniere, Multiplayer, WebSocket-Tickets)
- **Alle 10 Min**: Keep-Alive Self-Ping

## Troubleshooting

### Backend startet nicht
- Pruefe `DATABASE_URL` — muss mit `postgresql://` beginnen fuer Supabase
- Pruefe `SECRET_KEY` — darf nicht leer sein

### Scheduler Jobs laufen nicht
- Pruefe `BACKEND_URL` — wird fuer Keep-Alive gebraucht
- Pruefe Logs: `GET /api/admin/scheduler/status` zeigt alle Jobs

### 403 bei Admin-Endpoints
- Nur Emails aus der ADMIN_EMAILS Whitelist haben Zugriff
- Standard: `ahmadalkhalaf2019@gmail.com` und 4 weitere
