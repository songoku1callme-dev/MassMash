# LUMNOS App Testing

## Overview
LUMNOS is an AI-powered learning companion for German students (Abitur focus). The app has 35+ sidebar pages covering learning tools, gamification, social features, admin, and settings.

## Devin Secrets Needed
- `GROQ_API_KEY` — for AI chat functionality (Groq LLM)
- `CLERK_PUBLISHABLE_KEY` — for Clerk OAuth authentication
- `STRIPE_SECRET_KEY` — for payment/subscription features
- `TAVILY_API_KEY` — for internet research feature

## Setup

### Backend
```bash
cd eduai-backend
set -a && source .env && set +a
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd eduai-frontend
npm run dev -- --port 5175
```

## Authentication
- The app uses Clerk OAuth (Google, GitHub, Apple)
- For testing, use the dev token bypass: set `dev-max-token-lumnos` as the auth token
- This gives Max-level access (highest tier) with Test Admin user
- The dev token is configured in the backend's auth middleware

## Testing Strategy

### Phase 1: Auth Page
1. Navigate to the app URL
2. Verify AuthPage loads with Clerk SignIn widget
3. Verify register/login toggle works
4. Log in using Clerk OAuth or dev token

### Phase 2: Systematic Page Testing
Click through ALL 35 sidebar items and verify each loads:

**Main Features:** Dashboard, KI-Tutor, Quiz, IQ-Test, Lernpfad, Wissensdatenbank, Abitur-Simulation, Internet-Recherche

**Social/Gamification:** Gamification, Gruppen-Chats, Turniere, Karteikarten, Notizen, Prüfungs-Kalender, Multiplayer-Quiz, KI-Intelligenz, Pomodoro-Timer, Belohnungs-Shop, Challenges, Voice-Modus, Tägliche Quests, Saisonale Events, Lernpartner, Marketplace, Battle Pass

**Advanced:** Meine Statistiken, Mündliche Prüfung, Schulbuch-Scanner

**Account/Admin:** Eltern-Dashboard, Schul-Lizenzen, Admin-Panel, Forschungs-Zentrum, Datenschutz, Abo & Preise, Einstellungen

### Phase 3: Key Interactions
- Send a chat message and verify AI response
- Test SchoolPage package selection
- Verify Datenschutz shows all 9 DSGVO sections
- Check Impressum tab content

## Design System
- **Cyber-Zen Design**: Dark theme with glassmorphism
- Background: `linear-gradient(135deg, #0a0a1a 0%, #0d0d2b 50%, #0a0a1a 100%)`
- Cards: `rgba(255,255,255,0.03)` background, `1px solid rgba(255,255,255,0.08)` border, `blur(20px)` backdrop
- Accent colors: Purple/cyan gradients

## Known Issues & Workarounds
- Some pages need the sidebar scrolled down to access (pages after Voice-Modus are offscreen by default)
- Backend APIs may be unavailable on Vercel preview — pages should show static fallback content
- DatenschutzPage and SchoolPage have been fixed to use static fallbacks when backend is down
- The frontend dev server port might vary (5174 or 5175) — check the terminal output

## Tips
- Start recording AFTER setup is complete
- Annotate key moments during recording for easy review
- Test in order: visible sidebar items first, then scroll for remaining
- The app has ~35 sidebar items — budget enough time for complete testing
