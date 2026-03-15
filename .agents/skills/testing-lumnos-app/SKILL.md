# LUMNOS App Testing

## Overview
LUMNOS is a German AI tutoring app (FastAPI backend + React/Vite frontend) with 35+ pages and 68+ API endpoints.

## Devin Secrets Needed
- No special secrets needed for local testing
- Dev-token bypass: `dev-max-token-lumnos` auto-logs in as TestAdmin with Max tier
- Backend uses this token via `Authorization: Bearer dev-max-token-lumnos`

## Backend Setup
```bash
cd eduai-companion/eduai-backend
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Setup
```bash
cd eduai-companion/eduai-frontend
npm install
npm run dev
# Vite will auto-select an available port (usually 5175 or 5176)
```

## API Testing
- Use `Authorization: Bearer dev-max-token-lumnos` header
- IMPORTANT: BotProtectionMiddleware blocks curl/wget/python-urllib user agents
- Always add a browser User-Agent header: `User-Agent: Mozilla/5.0 ...`
- Example: `curl -H 'Authorization: Bearer dev-max-token-lumnos' -H 'User-Agent: Mozilla/5.0' http://localhost:8000/api/health`

## Frontend Testing
- App uses state-based routing (setCurrentPage), NOT React Router URLs
- All navigation happens via sidebar clicks, not URL changes
- The sidebar has 35 items — scroll down to see all of them
- Dev-token auto-login means no manual authentication needed

## Common Issues to Watch For
1. **Umlaut bugs**: Some pages use `ue/oe/ae` instead of proper `ü/ö/ä` (especially Datenschutz, Eltern-Dashboard)
2. **Empty states**: Shop, Marketplace, Challenges, Karteikarten, Notizen may show empty states — this is expected for new users but should have demo content
3. **Tier label mismatch**: Einstellungen page may show wrong subscription tier label
4. **Loading spinners**: Meine Statistiken and Forschungs-Zentrum may take a few seconds to load data
5. **BotProtectionMiddleware**: API calls from scripts get 403 Forbidden unless browser User-Agent is set

## Page Count
The sidebar has exactly 35 items:
Dashboard, KI-Tutor, Quiz, IQ-Test, Lernpfad, Wissensdatenbank, Abitur-Simulation, Internet-Recherche, Gamification, Gruppen-Chats, Turniere, Karteikarten, Notizen, Prüfungs-Kalender, Multiplayer-Quiz, KI-Intelligenz, Pomodoro-Timer, Belohnungs-Shop, Challenges, Voice-Modus, Tägliche Quests, Saisonale Events, Lernpartner, Marketplace, Battle Pass, Meine Statistiken, Mündliche Prüfung, Schulbuch-Scanner, Eltern-Dashboard, Schul-Lizenzen, Admin-Panel, Forschungs-Zentrum, Datenschutz, Abo & Preise, Einstellungen
