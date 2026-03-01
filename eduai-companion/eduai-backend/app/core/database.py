"""SQLite database setup with aiosqlite."""
import aiosqlite
import json
from datetime import datetime
from app.core.config import settings

DB_PATH = settings.db_path


async def get_db():
    """Get database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Initialize database tables."""
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

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

        CREATE TABLE IF NOT EXISTS research_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            results_json TEXT DEFAULT '[]',
            source_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
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
    ]
    for table, column, col_type in migrations:
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            await db.commit()
        except Exception:
            pass  # Column already exists

    # Sync subscription_tier with is_pro for existing users
    try:
        await db.execute(
            "UPDATE users SET subscription_tier = 'pro' WHERE is_pro = 1 AND subscription_tier = 'free'"
        )
        await db.commit()
    except Exception:
        pass  # is_pro column may not exist in very old DBs

    await db.close()
