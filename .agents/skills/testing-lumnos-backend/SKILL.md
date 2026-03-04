# Testing LUMNOS Backend

## Overview
LUMNOS is an AI tutoring app for German students. The backend is a FastAPI app with SQLite, the frontend is React+Vite.

## Devin Secrets Needed
- `GROQ_API_KEY` — Required for AI chat responses, TTS transcription, and quiz generation

## Local Setup

### Backend (Port 8000)
```bash
cd eduai-companion/eduai-backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Port 5175)
```bash
cd eduai-companion/eduai-frontend
npm run dev -- --port 5175 --host 0.0.0.0
```

### Dev Token
The backend has a dev-token bypass: `dev-max-token-lumnos`
- Returns user id=999, username="TestAdmin", email="admin@lumnos.de", tier="max"
- Use in curl: `-H "Authorization: Bearer dev-max-token-lumnos"`
- Frontend auto-login: Set `VITE_DEV_BYPASS=true` in `.env.local`

## Key Test Endpoints

### Notifications Bell (GET /api/notifications/bell)
- Requires auth token
- Returns notification items with `type` field (not `notification_type`)
- DB column is `type` in the `notifications` table

### Stats Overview (GET /api/stats/overview)
- Requires auth token
- Queries `gamification` table for `xp` (not `total_xp`) and `streak_days`
- Queries `iq_results` for `iq_score` (not `score`)
- All aggregates should use COALESCE or `or 0` fallback for NULL safety

### Admin Panel (GET /api/admin/stats)
- Requires admin authorization
- Admin check: id==1, username=="admin", id==999 (dev), tier=="max", email in ADMIN_EMAILS, or is_admin flag in DB
- Dev token user (id=999, auth_provider="dev") is always admin

### Chat / Fach-Detection (POST /api/chat)
- Send `{"message": "Erkläre mir Fotosynthese", "fach": "Allgemein"}`
- Response should tag `fach: "Biologie"` (not "Allgemein")
- Keywords are in `FACH_KEYWORDS` list in `ai_engine.py`
- Both "fotosynthese" and "photosynthese" should map to Biologie

### OCR Solve-Text (POST /api/ocr/solve-text)
- Accepts both JSON body (`{"text": "2x+3=7"}` or `{"equation": "2x+3=7"}`) and Form data
- The `SolveTextRequest` model has a `content` property that returns equation or text

### Voice TTS (POST /api/voice/tts)
- Accepts both Query params (`?text=Hallo&lang=de`) and JSON body (`{"text": "Hallo", "lang": "de"}`)
- Requires gTTS library installed

## UI Navigation
- **Notification Bell**: Top-right corner of the main content area (bell icon)
- **Meine Statistiken**: Sidebar link, may need to scroll down
- **Admin-Panel**: Sidebar link at bottom, only visible for admin/max-tier users
- **KI-Chat**: Sidebar link "KI-Tutor", type message in input at bottom

## Common Issues
- SQLite column names must match exactly — check `database.py` for schema definitions
- Dev token user might not have matching DB record (id=999 is synthetic)
- Admin authorization might fail if `_is_admin()` doesn't check all conditions (tier, dev token, email)
- Fach-Detection uses keyword scoring — both German spellings (foto/photo) should be covered
- FastAPI mixing JSON Body and Form parameters in same endpoint may cause 422 errors; test both paths separately
