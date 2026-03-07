# LUMNOS Backend Testing

## Setup

1. Navigate to `eduai-companion/eduai-backend/`
2. Install dependencies: `poetry install`
3. Run tests: `poetry run pytest -v --tb=short` (expect 24/24 passing)

## Local Backend

1. Start with dev mode: `LUMNOS_DEV_MODE=1 poetry run uvicorn app.main:app --port 8000`
2. Verify startup logs show: "Scheduler gestartet: X Jobs registriert"
3. Healthcheck: `GET http://localhost:8000/healthz`

## Authentication for Testing

- **Admin access**: Login with an admin-whitelisted email. The existing admin user in the dev DB has:
  - Username: `admin_e2e`
  - Email: `ahmadalkhalaf2019@gmail.com`
  - Login: `POST /api/auth/login` with `{"username": "admin_e2e", "password": "<password>"}`
- **Dev bypass** (non-admin): `POST /api/auth/dev-bypass` — creates/uses `qualitytest` user with Max tier but NOT admin rights
- **Register new admin**: `POST /api/auth/register` with any email from the ADMIN_EMAILS whitelist in `app/routes/admin.py`
- Auth header: `Authorization: Bearer <access_token>`

## Admin Endpoints

- `GET /api/admin/scheduler/status` — lists all scheduler jobs with next run times
- `POST /api/admin/scheduler/trigger/{job_id}` — manually trigger a job
- `GET /api/admin/stats` — platform statistics
- `GET /api/admin/is-admin` — check if current user is admin

## Key Job IDs for Testing

- `daily_quests` — safe to trigger, generates quests
- `shop_rotation` — rotates shop items
- `knowledge_update` — Tavily web search (needs TAVILY_API_KEY env var)
- `cleanup_ws_tickets` — cleanup expired tickets
- `streak_check` — check/reset streaks

## Database

- SQLite at `app.db` in the backend directory
- Can inspect with Python: `python3 -c "import sqlite3; ..."`
- `sqlite3` CLI may not be available; use Python instead

## Notes

- The Clerk JWT warning ("The specified alg value is not allowed") in logs is expected when using local JWT auth instead of Clerk
- LUMNOS_DEV_MODE=1 enables the dev-bypass endpoint; it's disabled when FLY_APP_NAME or RAILWAY_ENVIRONMENT is set
- All scheduler jobs use Europe/Berlin timezone
