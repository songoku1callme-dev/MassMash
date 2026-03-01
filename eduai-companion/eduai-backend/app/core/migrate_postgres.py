"""PostgreSQL migration script.

Generates the equivalent PostgreSQL schema from the existing SQLite schema.
Run this when migrating from SQLite to PostgreSQL.

Usage:
    # Print SQL to stdout:
    python -m app.core.migrate_postgres

    # Apply directly (requires DATABASE_URL env var):
    python -m app.core.migrate_postgres --apply

Requires: psycopg[binary] (already in pyproject.toml)
"""

import argparse
import os
import sys

# PostgreSQL-compatible DDL (equivalent of the SQLite schema in database.py)
POSTGRES_SCHEMA = """\
-- EduAI Companion — PostgreSQL Schema
-- Generated from SQLite schema in app/core/database.py

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    school_grade TEXT DEFAULT '10',
    school_type TEXT DEFAULT 'Gymnasium',
    preferred_language TEXT DEFAULT 'de',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    proficiency_level TEXT DEFAULT 'beginner',
    mastery_score DOUBLE PRECISION DEFAULT 0.0,
    topics_completed INTEGER DEFAULT 0,
    total_questions_answered INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    last_active TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, subject)
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT DEFAULT 'general',
    title TEXT DEFAULT 'New Chat',
    language TEXT DEFAULT 'de',
    messages JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quiz_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    quiz_type TEXT DEFAULT 'mcq',
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    score DOUBLE PRECISION DEFAULT 0.0,
    difficulty TEXT DEFAULT 'intermediate',
    questions JSONB DEFAULT '[]'::jsonb,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS learning_resources (
    id SERIAL PRIMARY KEY,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    difficulty TEXT DEFAULT 'intermediate',
    grade_level TEXT DEFAULT '10',
    language TEXT DEFAULT 'de',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quiz_answers (
    id SERIAL PRIMARY KEY,
    quiz_id TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(quiz_id, question_id)
);

CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    subject TEXT DEFAULT 'general',
    description TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_learning_profiles_user ON learning_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_results_user ON quiz_results(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_user ON activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created ON activity_log(created_at DESC);
"""


def print_schema() -> None:
    """Print the PostgreSQL schema to stdout."""
    print(POSTGRES_SCHEMA)


def apply_schema() -> None:
    """Apply the schema to a PostgreSQL database specified by DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        print("Example: DATABASE_URL=postgresql://user:pass@host:5432/eduai", file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg is not installed. Run: poetry add 'psycopg[binary]'", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to PostgreSQL...")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(POSTGRES_SCHEMA)
        conn.commit()
    print("Schema applied successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EduAI PostgreSQL migration")
    parser.add_argument("--apply", action="store_true", help="Apply schema to DATABASE_URL")
    args = parser.parse_args()

    if args.apply:
        apply_schema()
    else:
        print_schema()
"""
"""
