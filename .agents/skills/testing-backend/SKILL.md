# LUMNOS Backend Testing Skill

## Backend Location
`eduai-companion/eduai-backend/`

## Starting the Backend

### SQLite Mode (Local Dev)
```bash
LUMNOS_DEV_MODE=1 poetry run uvicorn app.main:app --port 8000
```

### PostgreSQL Mode (Supabase)
```bash
DATABASE_URL='postgresql://...' LUMNOS_DEV_MODE=1 poetry run uvicorn app.main:app --port 8000
```
The `DATABASE_URL` secret should be retrieved from saved secrets.

## Authentication

### Dev Token (Local Only)
- Token: `dev-max-token-lumnos`
- Header: `Authorization: Bearer dev-max-token-lumnos`
- Returns test user: id=999, is_pro=1, tier="max"
- **Blocked in production** (when FLY_APP_NAME or RAILWAY_ENVIRONMENT is set)

### Bot Protection
The `BotProtectionMiddleware` blocks requests with curl/bot user-agents.
- **Workaround**: Add `-H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"` to curl commands
- This only affects direct API testing, not browser-based testing

## PostgreSQL Test Setup

When testing with a fresh Supabase database:
1. Run `scripts/supabase_setup.py` to create all 52 tables
2. Insert test user (id=999) before using dev token:
```python
import asyncio, asyncpg
async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO users (id, username, hashed_password, email, full_name, school_grade, school_type,
                         preferred_language, is_pro, subscription_tier, ki_personality_id,
                         ki_personality_name, avatar_url, auth_provider)
        VALUES (999, 'TestAdmin', '$2b$12$dummy_hash', 'admin@lumnos.de',
                'Test Admin', '12', 'Gymnasium', 'de', 1, 'max', 1, 'Mentor', '', 'dev')
    """)
    await conn.close()
asyncio.run(main())
```

## Key Endpoints for Testing

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/ping` | GET | None | Keep-alive / health check |
| `/healthz` | GET | None | Production health check |
| `/api/chat` | POST | Required | Send chat message, creates session |
| `/api/chat/sessions` | GET | Required | List user's chat sessions |
| `/api/quiz/generate` | POST | Required | Generate quiz questions |

## Running Tests
```bash
# SQLite mode (default)
poetry run pytest -v --tb=short

# PostgreSQL mode
DATABASE_URL='postgresql://...' poetry run pytest -v --tb=short
```
Expected: 24/24 tests pass in both modes.

## Known Issues
- Scheduler jobs still use `aiosqlite.connect()` directly (pre-existing, out of scope for asyncpg PR)
- These produce non-fatal warnings in PostgreSQL mode but don't affect core functionality

## Dual-Mode Database Architecture
- `app/core/database.py` contains `AsyncPgConnection` wrapper
- Auto-converts `?` placeholders to `$1, $2, ...` for asyncpg
- Auto-converts SQLite functions: `datetime('now')` -> `NOW()`, etc.
- Auto-appends `RETURNING id` to INSERT statements for `lastrowid` support
- `_pg_row_to_dict()` converts PostgreSQL native types (datetime, UUID, Decimal) to strings
