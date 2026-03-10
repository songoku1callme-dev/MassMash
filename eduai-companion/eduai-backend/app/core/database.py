"""PR #50: Dual-mode database — SQLite (local) + PostgreSQL (Supabase production).

Checks DATABASE_URL env var:
  - If starts with "postgresql": uses asyncpg connection pool (fully async)
  - Otherwise: uses aiosqlite (current behavior)

The AsyncPgConnection wrapper auto-converts SQL placeholders:
  - SQLite: uses "?" natively
  - PostgreSQL: converts "?" → "$1, $2, ..." at runtime
  → No need to change any query in any route file!
"""
import os
import re
import logging
import aiosqlite
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID
from app.core.config import settings

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PR #50: Dual-Mode Database (SQLite / PostgreSQL)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATABASE_URL = os.getenv("DATABASE_URL", "")
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

# Placeholder for parameterized queries
# SQLite uses "?", PostgreSQL uses "$N" (asyncpg)
# Routes still use "?" — the wrapper converts automatically
PH = "?"  # Always use "?" in queries — auto-converted for PostgreSQL

DB_PATH = settings.db_path

# PostgreSQL connection pool (lazy-initialized)
_pg_pool = None


def _convert_placeholders(sql: str) -> str:
    """Convert SQLite '?' placeholders to asyncpg '$1, $2, ...' format.

    Also converts common SQLite-isms to PostgreSQL:
      - INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
      - INSERT OR REPLACE → INSERT ... ON CONFLICT DO NOTHING (simplified)
      - datetime('now') → NOW()
      - date('now') → CURRENT_DATE
      - date('now', '-N days') → CURRENT_DATE - INTERVAL 'N days'
      - datetime('now', '-N unit') → NOW() - INTERVAL 'N unit'
      - last_insert_rowid() → lastval()
    """
    result = sql

    # 1. Convert INSERT OR IGNORE/REPLACE (before other conversions)
    _append_on_conflict = False
    if re.search(r'INSERT\s+OR\s+IGNORE\s+INTO', result, re.IGNORECASE):
        result = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', result, flags=re.IGNORECASE)
        _append_on_conflict = True
    elif re.search(r'INSERT\s+OR\s+REPLACE\s+INTO', result, re.IGNORECASE):
        result = re.sub(r'INSERT\s+OR\s+REPLACE\s+INTO', 'INSERT INTO', result, flags=re.IGNORECASE)
        _append_on_conflict = True

    # 2. Convert SQLite datetime functions (BEFORE ? placeholder conversion)
    # datetime('now', '-N unit') → NOW() - INTERVAL 'N unit'
    result = re.sub(
        r"datetime\('now',\s*'(-?\d+)\s+(days?|hours?|minutes?|seconds?)'\)",
        lambda m: f"NOW() - INTERVAL '{abs(int(m.group(1)))} {m.group(2)}'",
        result, flags=re.IGNORECASE,
    )
    # date('now', '-N days') → CURRENT_DATE - INTERVAL 'N days'
    result = re.sub(
        r"date\('now',\s*'(-?\d+)\s+(days?|hours?|minutes?|seconds?)'\)",
        lambda m: f"CURRENT_DATE - INTERVAL '{abs(int(m.group(1)))} {m.group(2)}'",
        result, flags=re.IGNORECASE,
    )
    # Simple datetime('now') → NOW()
    result = re.sub(r"datetime\('now'\)", "NOW()", result, flags=re.IGNORECASE)
    # Simple date('now') → CURRENT_DATE
    result = re.sub(r"date\('now'\)", "CURRENT_DATE", result, flags=re.IGNORECASE)
    # last_insert_rowid() → lastval()
    result = re.sub(r"last_insert_rowid\(\)", "lastval()", result, flags=re.IGNORECASE)

    # 3. Convert ? placeholders to $1, $2, ...
    counter = 0

    def replacer(match: re.Match) -> str:
        nonlocal counter
        counter += 1
        return f"${counter}"

    # Replace ? that are NOT inside single-quoted strings
    # Simple approach: split by single quotes, only replace in odd segments
    parts = result.split("'")
    for i in range(0, len(parts), 2):  # Even indices = outside quotes
        parts[i] = re.sub(r"\?", replacer, parts[i])
    result = "'".join(parts)

    # 4. Append ON CONFLICT DO NOTHING for INSERT OR IGNORE/REPLACE
    if _append_on_conflict:
        result = result.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'

    return result


class AsyncPgConnection:
    """Wrapper around asyncpg.Connection that mimics aiosqlite interface.

    Converts:
      - '?' placeholders → '$1, $2, ...' (asyncpg format)
      - cursor.fetchone() → returns dict-like Record
      - cursor.fetchall() → returns list of dict-like Records
      - db.execute(sql, params) → conn.execute(converted_sql, *params)
      - db.commit() → conn.execute('COMMIT') (no-op in autocommit)
      - db.close() → releases connection back to pool
    """

    def __init__(self, conn):
        self._conn = conn
        self._in_transaction = False

    async def execute(self, sql: str, params=None):
        """Execute SQL with auto-converted placeholders.

        For INSERT statements, automatically appends RETURNING id
        so that cursor.lastrowid works (PostgreSQL doesn't track
        lastrowid like SQLite does).
        """
        converted = _convert_placeholders(sql)

        # For INSERT without RETURNING, add RETURNING id to capture lastrowid
        trimmed = converted.strip().upper()
        if trimmed.startswith("INSERT") and "RETURNING" not in trimmed:
            converted = converted.rstrip().rstrip(';') + ' RETURNING id'

        if params:
            result = await self._conn.fetch(converted, *params)
        else:
            result = await self._conn.fetch(converted)
        return AsyncPgCursor(result)

    async def executemany(self, sql: str, params_list):
        """Execute SQL for multiple parameter sets."""
        converted = _convert_placeholders(sql)
        for params in params_list:
            await self._conn.execute(converted, *params)

    async def executescript(self, sql: str):
        """Execute multiple SQL statements (for schema creation)."""
        await self._conn.execute(sql)

    async def commit(self):
        """Commit transaction (no-op if using asyncpg default autocommit)."""
        pass  # asyncpg handles transactions differently

    async def close(self):
        """Release connection back to pool."""
        pass  # Handled by get_db() finally block

    @property
    def row_factory(self):
        return None

    @row_factory.setter
    def row_factory(self, value):
        pass  # asyncpg Records already act like dicts


def _pg_row_to_dict(record) -> dict:
    """Convert asyncpg Record to dict with SQLite-compatible types.

    PostgreSQL returns native Python types (datetime, date, Decimal, UUID, etc.)
    but the Pydantic models and route code expect strings (as SQLite returns).
    This function converts those types to their string representations.
    """
    result = {}
    for key, value in dict(record).items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, date):
            result[key] = value.isoformat()
        elif isinstance(value, timedelta):
            result[key] = str(value)
        elif isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, UUID):
            result[key] = str(value)
        else:
            result[key] = value
    return result


class AsyncPgCursor:
    """Wrapper around asyncpg fetch results to mimic aiosqlite cursor."""

    def __init__(self, rows):
        self._rows = rows

    async def fetchone(self):
        if self._rows:
            return _pg_row_to_dict(self._rows[0])
        return None

    async def fetchall(self):
        return [_pg_row_to_dict(r) for r in self._rows]

    @property
    def lastrowid(self):
        """Get last inserted row ID (if available)."""
        if self._rows and "id" in self._rows[0]:
            return self._rows[0]["id"]
        return None


async def _get_pg_pool():
    """Get or create asyncpg connection pool."""
    global _pg_pool
    if _pg_pool is None:
        import asyncpg
        logger.info("Connecting to PostgreSQL (Supabase) via asyncpg...")
        _pg_pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=1,
            max_size=5,
            command_timeout=30,
            ssl="require",
        )
        logger.info("asyncpg connection pool created (1-5 connections)")
    return _pg_pool


async def get_db():
    """Get database connection (SQLite or PostgreSQL based on DATABASE_URL)."""
    if IS_POSTGRES:
        pool = await _get_pg_pool()
        conn = await pool.acquire()
        try:
            yield AsyncPgConnection(conn)
        finally:
            await pool.release(conn)
    else:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        # PR #46: 512MB RAM optimization — conservative cache for free tier
        await db.execute("PRAGMA cache_size=-8000")  # 8MB cache (safe for 512MB RAM)
        await db.execute("PRAGMA temp_store=MEMORY")
        try:
            yield db
        finally:
            await db.close()


async def init_db():
    """Initialize database tables (SQLite mode only).

    For PostgreSQL, use scripts/supabase_setup.py instead.
    """
    if IS_POSTGRES:
        logger.info("PostgreSQL mode: Skipping SQLite init_db (use supabase_setup.py)")
        return

    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    # PR #46: 512MB RAM optimization — conservative cache for free tier
    await db.execute("PRAGMA cache_size=-8000")  # 8MB cache (safe for 512MB RAM)
    await db.execute("PRAGMA temp_store=MEMORY")

    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            school_grade TEXT DEFAULT '10',
            school_type TEXT DEFAULT 'Gymnasium',
            preferred_language TEXT DEFAULT 'de',
            is_pro INTEGER DEFAULT 0,
            subscription_tier TEXT DEFAULT 'free',
            ki_personality_id INTEGER DEFAULT 1,
            ki_personality_name TEXT DEFAULT 'Freundlich',
            stripe_customer_id TEXT DEFAULT '',
            pro_since TEXT DEFAULT '',
            clerk_user_id TEXT DEFAULT '',
            avatar_url TEXT DEFAULT '',
            auth_provider TEXT DEFAULT 'local',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS learning_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            proficiency_level TEXT DEFAULT 'beginner',
            mastery_score REAL DEFAULT 0.0,
            topics_completed INTEGER DEFAULT 0,
            total_questions_answered INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            last_active TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, subject)
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT DEFAULT 'general',
            title TEXT DEFAULT 'New Chat',
            language TEXT DEFAULT 'de',
            messages TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            quiz_type TEXT DEFAULT 'mcq',
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            score REAL DEFAULT 0.0,
            difficulty TEXT DEFAULT 'intermediate',
            questions TEXT DEFAULT '[]',
            completed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS learning_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            difficulty TEXT DEFAULT 'intermediate',
            grade_level TEXT DEFAULT '10',
            language TEXT DEFAULT 'de',
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS quiz_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(quiz_id, question_id)
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            subject TEXT DEFAULT 'general',
            description TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic_name TEXT DEFAULT '',
            schwach INTEGER DEFAULT 0,
            feedback_score INTEGER DEFAULT 0,
            times_asked INTEGER DEFAULT 0,
            times_correct INTEGER DEFAULT 0,
            letzte_frage TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, topic_id)
        );

        CREATE TABLE IF NOT EXISTS abitur_simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 180,
            start_time TEXT DEFAULT (datetime('now')),
            pause_time TEXT DEFAULT '',
            paused_elapsed_seconds INTEGER DEFAULT 0,
            score REAL DEFAULT 0.0,
            note_punkte INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            questions TEXT DEFAULT '[]',
            answers TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS wochen_coach_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            plan_json TEXT DEFAULT '[]',
            week_count INTEGER DEFAULT 8,
            current_week INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gamification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            level_name TEXT DEFAULT 'Neuling',
            streak_days INTEGER DEFAULT 0,
            streak_last_date TEXT DEFAULT '',
            quizzes_completed INTEGER DEFAULT 0,
            chats_sent INTEGER DEFAULT 0,
            abitur_completed INTEGER DEFAULT 0,
            achievements TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS group_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT DEFAULT 'general',
            created_by INTEGER NOT NULL,
            members TEXT DEFAULT '[]',
            messages TEXT DEFAULT '[]',
            max_members INTEGER DEFAULT 10,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS research_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            results_json TEXT DEFAULT '[]',
            source_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            tier TEXT NOT NULL DEFAULT 'pro',
            duration_days INTEGER NOT NULL DEFAULT 30,
            max_uses INTEGER DEFAULT 0,
            current_uses INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS coupon_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            redeemed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (coupon_id) REFERENCES coupons(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(coupon_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            questions TEXT DEFAULT '[]',
            num_questions INTEGER DEFAULT 20,
            time_limit_seconds INTEGER DEFAULT 300,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tournament_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            time_taken_seconds INTEGER DEFAULT 0,
            answers TEXT DEFAULT '[]',
            submitted_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(tournament_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_user_id INTEGER,
            details TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (admin_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS iq_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            questions TEXT DEFAULT '[]',
            num_questions INTEGER DEFAULT 40,
            time_limit_seconds INTEGER DEFAULT 2700,
            status TEXT DEFAULT 'active',
            submitted_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS iq_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            iq_score INTEGER DEFAULT 100,
            iq_range TEXT DEFAULT '',
            percentile INTEGER DEFAULT 50,
            klassifikation TEXT DEFAULT '',
            kategorien TEXT DEFAULT '{}',
            staerken TEXT DEFAULT '[]',
            schwaechen TEXT DEFAULT '[]',
            raw_score REAL DEFAULT 0.0,
            max_score REAL DEFAULT 0.0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (test_id) REFERENCES iq_tests(id)
        );

        CREATE TABLE IF NOT EXISTS chat_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            message_index INTEGER NOT NULL,
            rating TEXT NOT NULL DEFAULT 'positive',
            reason TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS multiplayer_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT UNIQUE NOT NULL,
            host_id INTEGER NOT NULL,
            subject TEXT DEFAULT 'general',
            topic TEXT DEFAULT '',
            status TEXT DEFAULT 'waiting',
            max_players INTEGER DEFAULT 8,
            num_questions INTEGER DEFAULT 10,
            questions TEXT DEFAULT '[]',
            players TEXT DEFAULT '[]',
            scores TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (host_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS school_licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            teacher_id INTEGER NOT NULL,
            class_code TEXT UNIQUE NOT NULL,
            tier TEXT DEFAULT 'max',
            max_students INTEGER DEFAULT 30,
            students TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            expires_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            p256dh TEXT DEFAULT '',
            auth_key TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, endpoint)
        );

        CREATE TABLE IF NOT EXISTS pomodoro_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT DEFAULT 'general',
            duration_minutes INTEGER DEFAULT 25,
            xp_earned INTEGER DEFAULT 25,
            completed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS shop_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT DEFAULT '',
            category TEXT DEFAULT '',
            price_xp INTEGER DEFAULT 0,
            purchased_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS challenges_db (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id TEXT UNIQUE NOT NULL,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            subject TEXT DEFAULT 'general',
            target_score INTEGER DEFAULT 80,
            xp_reward INTEGER DEFAULT 100,
            deadline TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS challenge_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'joined',
            score INTEGER DEFAULT 0,
            completed_at TEXT DEFAULT '',
            joined_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(challenge_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS spaced_repetition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            next_review TEXT DEFAULT (datetime('now')),
            interval_days INTEGER DEFAULT 1,
            ease_factor REAL DEFAULT 2.5,
            repetitions INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, subject, topic)
        );

        CREATE TABLE IF NOT EXISTS daily_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quest_id TEXT NOT NULL,
            quest_date TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            xp_reward INTEGER DEFAULT 50,
            target INTEGER DEFAULT 1,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, quest_id, quest_date)
        );

        CREATE TABLE IF NOT EXISTS parent_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER NOT NULL,
            child_id INTEGER NOT NULL,
            verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (parent_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (child_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(parent_id, child_id)
        );

        CREATE TABLE IF NOT EXISTS seasonal_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            event_type TEXT DEFAULT 'challenge',
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            rewards_json TEXT DEFAULT '{}',
            challenges_json TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ki_relationship (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            trust_level REAL DEFAULT 1.0,
            known_name TEXT DEFAULT '',
            known_hobbies TEXT DEFAULT '[]',
            preferred_explanation TEXT DEFAULT 'Analogien',
            difficult_topics TEXT DEFAULT '[]',
            interaction_count INTEGER DEFAULT 0,
            last_interaction TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS marketplace_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            price_cents INTEGER DEFAULT 0,
            item_type TEXT DEFAULT 'quiz_set',
            content_json TEXT DEFAULT '[]',
            downloads INTEGER DEFAULT 0,
            rating REAL DEFAULT 0.0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL DEFAULT '',
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            link TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT DEFAULT 'general',
            front TEXT NOT NULL DEFAULT '',
            back TEXT NOT NULL DEFAULT '',
            difficulty INTEGER DEFAULT 0,
            next_review TEXT DEFAULT (datetime('now')),
            interval_days INTEGER DEFAULT 1,
            ease_factor REAL DEFAULT 2.5,
            repetitions INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS xp_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL DEFAULT 0,
            source TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS question_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            fach TEXT NOT NULL,
            thema TEXT DEFAULT '',
            frage_hash TEXT NOT NULL,
            gesehen_am TEXT DEFAULT (datetime('now')),
            richtig INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_question_history_user_fach
            ON question_history(user_id, fach, gesehen_am);

        -- Supreme 13.0 Phase 5-6: Performance indexes for production scale
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_clerk_id ON users(clerk_user_id);
        CREATE INDEX IF NOT EXISTS idx_users_tier ON users(subscription_tier);
        CREATE INDEX IF NOT EXISTS idx_quiz_results_user ON quiz_results(user_id, completed_at);
        CREATE INDEX IF NOT EXISTS idx_quiz_results_subject ON quiz_results(user_id, subject);
        CREATE INDEX IF NOT EXISTS idx_activity_log_user ON activity_log(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_activity_log_type ON activity_log(user_id, activity_type, created_at);
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id, updated_at);
        CREATE INDEX IF NOT EXISTS idx_gamification_user ON gamification(user_id);
        CREATE INDEX IF NOT EXISTS idx_tournaments_date ON tournaments(date, status);
        CREATE INDEX IF NOT EXISTS idx_tournament_entries_user ON tournament_entries(user_id, tournament_id);
        CREATE INDEX IF NOT EXISTS idx_daily_quests_user ON daily_quests(user_id, quest_date);
        CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at);
        CREATE INDEX IF NOT EXISTS idx_spaced_repetition_review ON spaced_repetition(user_id, next_review);
        CREATE INDEX IF NOT EXISTS idx_flashcards_review ON flashcards(user_id, next_review);
        CREATE INDEX IF NOT EXISTS idx_ki_relationship_user ON ki_relationship(user_id);
        -- Supreme 13.0 Phase 10: Noten-Prognose table
        CREATE TABLE IF NOT EXISTS noten_prognose (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            fach TEXT NOT NULL,
            aktuelle_note REAL,
            prognose_note REAL,
            trend TEXT DEFAULT 'stabil',
            confidence REAL DEFAULT 0.5,
            analyse TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS battle_pass (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            saison TEXT DEFAULT 'Fruehling 2026',
            current_level INTEGER DEFAULT 1,
            current_xp INTEGER DEFAULT 0,
            xp_per_level INTEGER DEFAULT 200,
            claimed_rewards TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- Supreme 13.0 Phase 5-6: Performance indexes (after all tables created)
        CREATE INDEX IF NOT EXISTS idx_battle_pass_user ON battle_pass(user_id);
        CREATE INDEX IF NOT EXISTS idx_xp_log_user ON xp_log(user_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_noten_prognose_user ON noten_prognose(user_id, fach);

        CREATE TABLE IF NOT EXISTS parent_link_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER NOT NULL,
            child_email TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (parent_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS marketplace_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            payment_intent_id TEXT DEFAULT '',
            amount_cents INTEGER DEFAULT 0,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES marketplace_items(id),
            UNIQUE(user_id, item_id)
        );

        -- Fächer-Expansion 5.0 Block 5: Schulbuch-Scanner scans
        CREATE TABLE IF NOT EXISTS schulbuch_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            fach TEXT DEFAULT 'Allgemein',
            ocr_text TEXT DEFAULT '',
            analyse TEXT DEFAULT '{}',
            quiz TEXT DEFAULT '[]',
            karteikarten TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_schulbuch_scans_user ON schulbuch_scans(user_id, created_at);

        -- Final Polish 5.1 Block 1: WebSocket tickets table
        CREATE TABLE IF NOT EXISTS ws_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_ws_tickets_ticket ON ws_tickets(ticket, expires_at);

        -- Block C: Confidence Tracking + Blind-Spot Detection
        CREATE TABLE IF NOT EXISTS quiz_confidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quiz_id INTEGER,
            fach TEXT DEFAULT 'Allgemein',
            thema TEXT DEFAULT '',
            confidence INTEGER DEFAULT 3,
            war_richtig INTEGER DEFAULT 0,
            blind_spot INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_quiz_confidence_user ON quiz_confidence(user_id, fach, blind_spot);

        -- Fächer-Expansion 5.0 Block 4: Lehrplan-Themen cache
        CREATE TABLE IF NOT EXISTS lehrplan_themen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fach TEXT NOT NULL,
            bundesland TEXT DEFAULT '',
            themen TEXT DEFAULT '[]',
            quelle TEXT DEFAULT '',
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(fach, bundesland)
        );

        -- LUMNOS Self-Evolution: Knowledge Updates (Block 1)
        CREATE TABLE IF NOT EXISTS knowledge_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fach TEXT NOT NULL,
            thema TEXT NOT NULL,
            quellen_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_knowledge_updates_date ON knowledge_updates(created_at);

        -- LUMNOS Self-Evolution: Prompt-Vorschläge (Block 3)
        CREATE TABLE IF NOT EXISTS prompt_vorschlaege (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fach TEXT NOT NULL,
            probleme TEXT DEFAULT '',
            neuer_prompt TEXT DEFAULT '',
            feedback_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ausstehend',
            created_at TEXT DEFAULT (datetime('now')),
            genehmigt_am TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_prompt_vorschlaege_status ON prompt_vorschlaege(status);

        -- LUMNOS Self-Evolution: Chat Feedbacks v2 (Block 3)
        CREATE TABLE IF NOT EXISTS chat_feedbacks_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message_id TEXT DEFAULT '',
            frage TEXT DEFAULT '',
            antwort TEXT DEFAULT '',
            bewertung TEXT DEFAULT 'positiv',
            fach TEXT DEFAULT '',
            kommentar TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_chat_feedbacks_v2_fach ON chat_feedbacks_v2(fach, bewertung, created_at);

        -- PR #45: Weekly Challenges table (scheduler job)
        CREATE TABLE IF NOT EXISTS weekly_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            subject TEXT DEFAULT 'general',
            target_score INTEGER DEFAULT 80,
            xp_reward INTEGER DEFAULT 150,
            deadline TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_weekly_challenges_active ON weekly_challenges(is_active, deadline);

        -- PR #45: Shop Rotations table (scheduler job)
        -- PR #46 FIX: week_date + items_json columns match rotate_shop_items() function
        CREATE TABLE IF NOT EXISTS shop_rotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_date TEXT NOT NULL UNIQUE,
            items_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_shop_rotations_week ON shop_rotations(week_date);
    """)

    await db.commit()

    # --- Migrations for existing databases ---
    # Add new columns if they don't exist (safe for fresh + existing DBs)
    migrations = [
        ("users", "is_pro", "INTEGER DEFAULT 0"),
        ("users", "subscription_tier", "TEXT DEFAULT 'free'"),
        ("users", "ki_personality_id", "INTEGER DEFAULT 1"),
        ("users", "ki_personality_name", "TEXT DEFAULT 'Freundlich'"),
        ("users", "stripe_customer_id", "TEXT DEFAULT ''"),
        ("users", "pro_since", "TEXT DEFAULT ''"),
        ("users", "clerk_user_id", "TEXT DEFAULT ''"),
        ("users", "avatar_url", "TEXT DEFAULT ''"),
        ("users", "auth_provider", "TEXT DEFAULT 'local'"),
        ("users", "pro_expires_at", "TEXT DEFAULT ''"),
        ("users", "billing_period", "TEXT DEFAULT 'monthly'"),
        ("users", "is_admin", "INTEGER DEFAULT 0"),
        # Supreme 11.0: KI-Memory extended columns
        ("ki_relationship", "last_emotion", "TEXT DEFAULT ''"),
        ("ki_relationship", "erfolge_erwaehnt", "TEXT DEFAULT '[]'"),
        ("ki_relationship", "lieblingserklärung", "TEXT DEFAULT 'Analogien'"),
        # Supreme 11.0: Parent link verification
        ("parent_links", "verification_token", "TEXT DEFAULT ''"),
        # Supreme 13.0: User streak tracking
        ("users", "streak_days", "INTEGER DEFAULT 0"),
        ("users", "longest_streak", "INTEGER DEFAULT 0"),
        ("users", "last_active", "TEXT DEFAULT ''"),
        # Fächer-Expansion 5.0 Block 3: Bundesland fields
        ("users", "bundesland", "TEXT DEFAULT ''"),
        ("users", "klasse", "INTEGER DEFAULT 10"),
        ("users", "schultyp_detail", "TEXT DEFAULT 'Gymnasium'"),
        # Final Polish 5.1 Block 1: Additional user profile fields
        ("users", "favoriten_fächer", "TEXT DEFAULT '[]'"),
    ]
    for table, column, col_type in migrations:
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            await db.commit()
        except Exception:
            pass  # Column already exists

    # --- Dev user for testing (id=999) ---
    # Ensures the dev-max-token-lumnos bypass user exists in the DB
    # so foreign key constraints don't fail.
    try:
        await db.execute(
            """INSERT OR IGNORE INTO users
            (id, email, username, hashed_password, full_name, school_grade,
             school_type, preferred_language, is_pro, subscription_tier,
             ki_personality_id, ki_personality_name, auth_provider)
            VALUES (999, 'admin@lumnos.de', 'TestAdmin', 'dev-no-login',
                    'Test Admin', '12', 'Gymnasium', 'de', 1, 'max',
                    1, 'Mentor', 'dev')""",
        )
        await db.commit()
    except Exception:
        pass  # User already exists or table not ready

    # Sync subscription_tier with is_pro for existing users
    try:
        await db.execute(
            "UPDATE users SET subscription_tier = 'pro' WHERE is_pro = 1 AND subscription_tier = 'free'"
        )
        await db.commit()
    except Exception:
        pass  # is_pro column may not exist in very old DBs

    # Hardcoded admin whitelist — these users ALWAYS get permanent Max tier
    # They can NEVER be downgraded
    admin_emails = [
        "ahmadalkhalaf2019@gmail.com",
        "ahmadalkhalaf20024@gmail.com",
        "ahmadalkhalaf1245@gmail.com",
        "songoku1callme@gmail.com",
        "261g2g261@gmail.com",
    ]
    try:
        # Shield 4: Use parameterized queries — never interpolate user data into SQL
        placeholders = ", ".join("?" for _ in admin_emails)
        await db.execute(
            f"UPDATE users SET subscription_tier = 'max', is_pro = 1, is_admin = 1, "
            f"pro_expires_at = '' WHERE id = 1 OR username = 'admin' OR email IN ({placeholders})",
            tuple(admin_emails),
        )
        await db.commit()
    except Exception:
        pass

    await db.close()
