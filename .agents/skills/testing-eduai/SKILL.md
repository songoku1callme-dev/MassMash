# EduAI Companion — E2E Testing Skill

## Devin Secrets Needed
- None required for local testing (template fallbacks work without API keys)
- `GROQ_API_KEY` — needed on Fly.io for real AI-generated quiz questions (without it, template questions are used)

## Setup
1. Start backend: `cd eduai-backend && EDUAI_DEV_MODE=1 poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Start frontend: `cd eduai-frontend && npm run dev`
3. Frontend runs at http://localhost:5173, backend at http://localhost:8000
4. `EDUAI_DEV_MODE=1` enables CORS `*` for local development

## Auth Flow
- Navigate to http://localhost:5173 → AuthPage shows Login form
- Click "Noch kein Konto? Jetzt registrieren" to switch to Register
- Fill in: Name, Username, Email, Password (min 6 chars), Klasse (5-13), Schulart (Gymnasium/Realschule/Gesamtschule), Sprache (de/en)
- Click "Konto erstellen" → redirected to Dashboard
- User info shown in sidebar bottom (name, school, grade)
- JWT token stored in localStorage

## Navigation
All pages accessible via left sidebar:
- Dashboard, KI-Tutor, Quiz, Lernpfad, Wissensdatenbank, Abitur-Simulation, Internet-Recherche, Gamification, Gruppen-Chats, Abo & Preise, Einstellungen

## Feature Testing Notes

### Quiz 3.0
- Quiz setup page shows 16 subject grid, topic selection, quiz type, question count, difficulty
- **2-column topic selection**: Left = "Vordefinierte Themen" dropdown (preset topics per subject), Right = "Eigenes Thema eingeben" (free text, Pro+ required)
- **Tier gating**: Custom topic (free text) returns 403 for free users — this is expected. Use preset topic dropdown for free-tier testing.
- Quiz types: Gemischt, Multiple Choice, Wahr/Falsch, Lückentext, Freitext
- Question counts: 5, 10, 20, 50
- Difficulty: Anfänger, Mittel, Schwer
- After answering, KI-Erklärung shows explanation
- Results show percentage, score, level change, and +XP earned
- Without GROQ_API_KEY, template questions are generated (basic math). With the key, Groq generates topic-specific questions.

### Gamification Dashboard
- Shows 4 stats cards: Level, XP gesamt, Tage Streak, Quizzes
- XP progress bar with level name and XP needed for next level
- 3 tabs: Übersicht (activity counts + level system), Achievements (8 achievement cards, earned ones highlighted), Rangliste (Top 10 weekly leaderboard)
- XP is awarded: +10 for quiz, +5 for chat, +50 for abitur
- Registration gives initial XP (25)

### Gruppen-Chats
- **Tier-gated**: Free users see "Max-Abo erforderlich" lock page
- Max users see: group list, create group form (name + 14 subject options), chat view with 5-second polling
- To test the full groups UI, the user needs Max tier (either via Stripe payment or manually updating DB)

### Abitur 3.0
- Free topic input field available
- Tavily searches for Abituraufgaben 2024-2026 (requires TAVILY_API_KEY)
- Without Tavily key, may fall back to template questions

## Common Issues
- If backend returns 403 on quiz/generate with custom topic: user is free tier, custom topics require Pro+
- If backend shows "SECRET_KEY not set" warning: normal for local dev, sessions won't survive restarts
- "Nächste Frage" button may need clicking via coordinates if devinid click times out — use `click_coordinates` as fallback
- Frontend .env has `VITE_API_URL=http://localhost:8000` — don't commit changes to this file
