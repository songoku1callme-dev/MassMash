"""PostgreSQL migration script.

Generates the equivalent PostgreSQL schema from the existing SQLite schema.
Run this when migrating from SQLite to PostgreSQL.

Usage:
    # Print SQL to stdout:
    python -m app.core.migrate_postgres

    # Apply directly (requires DATABASE_URL env var):
    python -m app.core.migrate_postgres --apply

    # Migrate data from SQLite to PostgreSQL:
    python -m app.core.migrate_postgres --migrate-data --sqlite-path ./app.db

Requires: psycopg[binary] (already in pyproject.toml)
"""

import argparse
import os
import sys

# ---------------------------------------------------------------------------
# PostgreSQL-compatible DDL — covers ALL 50 tables from database.py
# ---------------------------------------------------------------------------
POSTGRES_SCHEMA = """\
-- =========================================================================
-- Lumnos Companion — PostgreSQL Schema (Complete)
-- Generated from SQLite schema in app/core/database.py
-- Tables: 50 | Indexes: 27+
-- =========================================================================

-- -------------------------------------------------------------------------
-- 1. users — Core user table
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
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
    pro_expires_at TEXT DEFAULT '',
    billing_period TEXT DEFAULT 'monthly',
    is_admin INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_active TEXT DEFAULT '',
    bundesland TEXT DEFAULT '',
    klasse INTEGER DEFAULT 10,
    schultyp_detail TEXT DEFAULT 'Gymnasium',
    favoriten_faecher TEXT DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 2. learning_profiles — Per-subject proficiency tracking
-- -------------------------------------------------------------------------
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

-- -------------------------------------------------------------------------
-- 3. chat_sessions — KI chat history (messages stored as JSONB)
-- -------------------------------------------------------------------------
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

-- -------------------------------------------------------------------------
-- 4. quiz_results — Completed quiz scores
-- -------------------------------------------------------------------------
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

-- -------------------------------------------------------------------------
-- 5. learning_resources — Educational content library
-- -------------------------------------------------------------------------
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

-- -------------------------------------------------------------------------
-- 6. quiz_answers — Correct answers + explanations for quiz questions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quiz_answers (
    id SERIAL PRIMARY KEY,
    quiz_id TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(quiz_id, question_id)
);

-- -------------------------------------------------------------------------
-- 7. activity_log — User activity tracking
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    subject TEXT DEFAULT 'general',
    description TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 8. user_memories — KI memory of user strengths/weaknesses per topic
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    topic_name TEXT DEFAULT '',
    schwach INTEGER DEFAULT 0,
    feedback_score INTEGER DEFAULT 0,
    times_asked INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0,
    letzte_frage TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, topic_id)
);

-- -------------------------------------------------------------------------
-- 9. abitur_simulations — Abitur exam simulations
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS abitur_simulations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    duration_minutes INTEGER DEFAULT 180,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    pause_time TEXT DEFAULT '',
    paused_elapsed_seconds INTEGER DEFAULT 0,
    score DOUBLE PRECISION DEFAULT 0.0,
    note_punkte INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    questions JSONB DEFAULT '[]'::jsonb,
    answers JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 10. wochen_coach_plans — Weekly learning plans
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wochen_coach_plans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    plan_json JSONB DEFAULT '[]'::jsonb,
    week_count INTEGER DEFAULT 8,
    current_week INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 11. gamification — XP, level, streaks, achievements
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gamification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    level_name TEXT DEFAULT 'Neuling',
    streak_days INTEGER DEFAULT 0,
    streak_last_date TEXT DEFAULT '',
    quizzes_completed INTEGER DEFAULT 0,
    chats_sent INTEGER DEFAULT 0,
    abitur_completed INTEGER DEFAULT 0,
    achievements JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 12. group_chats — Group study sessions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS group_chats (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    subject TEXT DEFAULT 'general',
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    members JSONB DEFAULT '[]'::jsonb,
    messages JSONB DEFAULT '[]'::jsonb,
    max_members INTEGER DEFAULT 10,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 13. research_results — Internet research results (Tavily/Wikipedia)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS research_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    results_json JSONB DEFAULT '[]'::jsonb,
    source_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 14. coupons — Admin-created discount/upgrade coupons
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coupons (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    tier TEXT NOT NULL DEFAULT 'pro',
    duration_days INTEGER NOT NULL DEFAULT 30,
    max_uses INTEGER DEFAULT 0,
    current_uses INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 15. coupon_redemptions — Coupon usage tracking
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coupon_redemptions (
    id SERIAL PRIMARY KEY,
    coupon_id INTEGER NOT NULL REFERENCES coupons(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    redeemed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(coupon_id, user_id)
);

-- -------------------------------------------------------------------------
-- 16. tournaments — Weekly quiz tournaments
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tournaments (
    id SERIAL PRIMARY KEY,
    subject TEXT NOT NULL,
    date TEXT NOT NULL,
    status TEXT DEFAULT 'scheduled',
    questions JSONB DEFAULT '[]'::jsonb,
    num_questions INTEGER DEFAULT 20,
    time_limit_seconds INTEGER DEFAULT 300,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 17. tournament_entries — User tournament participation
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tournament_entries (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    score INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    time_taken_seconds INTEGER DEFAULT 0,
    answers JSONB DEFAULT '[]'::jsonb,
    submitted_at TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tournament_id, user_id)
);

-- -------------------------------------------------------------------------
-- 18. admin_logs — Admin action audit trail
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    target_user_id INTEGER,
    details TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 19. iq_tests — IQ test sessions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS iq_tests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    questions JSONB DEFAULT '[]'::jsonb,
    num_questions INTEGER DEFAULT 40,
    time_limit_seconds INTEGER DEFAULT 2700,
    status TEXT DEFAULT 'active',
    submitted_at TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 20. iq_results — IQ test results + analysis
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS iq_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_id INTEGER NOT NULL REFERENCES iq_tests(id),
    iq_score INTEGER DEFAULT 100,
    iq_range TEXT DEFAULT '',
    percentile INTEGER DEFAULT 50,
    klassifikation TEXT DEFAULT '',
    kategorien JSONB DEFAULT '{}'::jsonb,
    staerken JSONB DEFAULT '[]'::jsonb,
    schwaechen JSONB DEFAULT '[]'::jsonb,
    raw_score DOUBLE PRECISION DEFAULT 0.0,
    max_score DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 21. chat_feedback — Chat message ratings (v1)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL,
    message_index INTEGER NOT NULL,
    rating TEXT NOT NULL DEFAULT 'positive',
    reason TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 22. multiplayer_rooms — Multiplayer quiz rooms
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS multiplayer_rooms (
    id SERIAL PRIMARY KEY,
    room_code TEXT UNIQUE NOT NULL,
    host_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT DEFAULT 'general',
    topic TEXT DEFAULT '',
    status TEXT DEFAULT 'waiting',
    max_players INTEGER DEFAULT 8,
    num_questions INTEGER DEFAULT 10,
    questions JSONB DEFAULT '[]'::jsonb,
    players JSONB DEFAULT '[]'::jsonb,
    scores JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 23. school_licenses — School/class license management
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS school_licenses (
    id SERIAL PRIMARY KEY,
    school_name TEXT NOT NULL,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    class_code TEXT UNIQUE NOT NULL,
    tier TEXT DEFAULT 'max',
    max_students INTEGER DEFAULT 30,
    students JSONB DEFAULT '[]'::jsonb,
    is_active INTEGER DEFAULT 1,
    expires_at TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 24. push_subscriptions — Web Push notification subscriptions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    p256dh TEXT DEFAULT '',
    auth_key TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, endpoint)
);

-- -------------------------------------------------------------------------
-- 25. pomodoro_sessions — Pomodoro timer completions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pomodoro_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT DEFAULT 'general',
    duration_minutes INTEGER DEFAULT 25,
    xp_earned INTEGER DEFAULT 25,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 26. shop_purchases — XP shop item purchases
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS shop_purchases (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    item_name TEXT DEFAULT '',
    category TEXT DEFAULT '',
    price_xp INTEGER DEFAULT 0,
    purchased_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 27. challenges_db — User-created challenges
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS challenges_db (
    id SERIAL PRIMARY KEY,
    challenge_id TEXT UNIQUE NOT NULL,
    creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    subject TEXT DEFAULT 'general',
    target_score INTEGER DEFAULT 80,
    xp_reward INTEGER DEFAULT 100,
    deadline TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 28. challenge_progress — Challenge participation tracking
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS challenge_progress (
    id SERIAL PRIMARY KEY,
    challenge_id TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'joined',
    score INTEGER DEFAULT 0,
    completed_at TEXT DEFAULT '',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(challenge_id, user_id)
);

-- -------------------------------------------------------------------------
-- 29. spaced_repetition — Spaced repetition scheduling
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS spaced_repetition (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    next_review TIMESTAMPTZ DEFAULT NOW(),
    interval_days INTEGER DEFAULT 1,
    ease_factor DOUBLE PRECISION DEFAULT 2.5,
    repetitions INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, subject, topic)
);

-- -------------------------------------------------------------------------
-- 30. daily_quests — Daily quest tracking
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_quests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quest_id TEXT NOT NULL,
    quest_date TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    xp_reward INTEGER DEFAULT 50,
    target INTEGER DEFAULT 1,
    progress INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, quest_id, quest_date)
);

-- -------------------------------------------------------------------------
-- 31. parent_links — Parent-child account links
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parent_links (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    child_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    verified INTEGER DEFAULT 0,
    verification_token TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(parent_id, child_id)
);

-- -------------------------------------------------------------------------
-- 32. seasonal_events — Seasonal challenges and events
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS seasonal_events (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    event_type TEXT DEFAULT 'challenge',
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    rewards_json JSONB DEFAULT '{}'::jsonb,
    challenges_json JSONB DEFAULT '[]'::jsonb,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 33. ki_relationship — KI personality memory per user
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ki_relationship (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    trust_level DOUBLE PRECISION DEFAULT 1.0,
    known_name TEXT DEFAULT '',
    known_hobbies JSONB DEFAULT '[]'::jsonb,
    preferred_explanation TEXT DEFAULT 'Analogien',
    difficult_topics JSONB DEFAULT '[]'::jsonb,
    interaction_count INTEGER DEFAULT 0,
    last_interaction TIMESTAMPTZ DEFAULT NOW(),
    last_emotion TEXT DEFAULT '',
    erfolge_erwaehnt JSONB DEFAULT '[]'::jsonb,
    lieblingserklaerung TEXT DEFAULT 'Analogien',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 34. marketplace_items — User-created content marketplace
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marketplace_items (
    id SERIAL PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    price_cents INTEGER DEFAULT 0,
    item_type TEXT DEFAULT 'quiz_set',
    content_json JSONB DEFAULT '[]'::jsonb,
    downloads INTEGER DEFAULT 0,
    rating DOUBLE PRECISION DEFAULT 0.0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 35. notifications — In-app notifications
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    type TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    link TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 36. flashcards — Flashcard system with spaced repetition
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flashcards (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT DEFAULT 'general',
    front TEXT NOT NULL DEFAULT '',
    back TEXT NOT NULL DEFAULT '',
    difficulty INTEGER DEFAULT 0,
    next_review TIMESTAMPTZ DEFAULT NOW(),
    interval_days INTEGER DEFAULT 1,
    ease_factor DOUBLE PRECISION DEFAULT 2.5,
    repetitions INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 37. xp_log — XP earning history
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS xp_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL DEFAULT 0,
    source TEXT DEFAULT '',
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 38. question_history — Quiz question dedup tracking
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS question_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fach TEXT NOT NULL,
    thema TEXT DEFAULT '',
    frage_hash TEXT NOT NULL,
    gesehen_am TIMESTAMPTZ DEFAULT NOW(),
    richtig INTEGER DEFAULT 0
);

-- -------------------------------------------------------------------------
-- 39. noten_prognose — Grade prediction per subject
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS noten_prognose (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fach TEXT NOT NULL,
    aktuelle_note DOUBLE PRECISION,
    prognose_note DOUBLE PRECISION,
    trend TEXT DEFAULT 'stabil',
    confidence DOUBLE PRECISION DEFAULT 0.5,
    analyse TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 40. battle_pass — Season battle pass tracking
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS battle_pass (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    saison TEXT DEFAULT 'Fruehling 2026',
    current_level INTEGER DEFAULT 1,
    current_xp INTEGER DEFAULT 0,
    xp_per_level INTEGER DEFAULT 200,
    claimed_rewards JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 41. parent_link_requests — Pending parent-child link requests
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parent_link_requests (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    child_email TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 42. marketplace_purchases — Marketplace item purchases
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marketplace_purchases (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES marketplace_items(id),
    payment_intent_id TEXT DEFAULT '',
    amount_cents INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, item_id)
);

-- -------------------------------------------------------------------------
-- 43. schulbuch_scans — OCR textbook scans
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schulbuch_scans (
    id SERIAL PRIMARY KEY,
    scan_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fach TEXT DEFAULT 'Allgemein',
    ocr_text TEXT DEFAULT '',
    analyse JSONB DEFAULT '{}'::jsonb,
    quiz JSONB DEFAULT '[]'::jsonb,
    karteikarten JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 44. ws_tickets — WebSocket authentication tickets
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ws_tickets (
    id SERIAL PRIMARY KEY,
    ticket TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 45. quiz_confidence — Confidence tracking + blind spot detection
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quiz_confidence (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quiz_id INTEGER,
    fach TEXT DEFAULT 'Allgemein',
    thema TEXT DEFAULT '',
    confidence INTEGER DEFAULT 3,
    war_richtig INTEGER DEFAULT 0,
    blind_spot INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 46. lehrplan_themen — Curriculum topics cache (per Bundesland)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lehrplan_themen (
    id SERIAL PRIMARY KEY,
    fach TEXT NOT NULL,
    bundesland TEXT DEFAULT '',
    themen JSONB DEFAULT '[]'::jsonb,
    quelle TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fach, bundesland)
);

-- -------------------------------------------------------------------------
-- 47. knowledge_updates — Nightly self-learning crawl results
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_updates (
    id SERIAL PRIMARY KEY,
    fach TEXT NOT NULL,
    thema TEXT NOT NULL,
    quellen_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 48. prompt_vorschlaege — AI-generated prompt improvement suggestions
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prompt_vorschlaege (
    id SERIAL PRIMARY KEY,
    fach TEXT NOT NULL,
    probleme TEXT DEFAULT '',
    neuer_prompt TEXT DEFAULT '',
    feedback_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ausstehend',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    genehmigt_am TEXT DEFAULT ''
);

-- -------------------------------------------------------------------------
-- 49. chat_feedbacks_v2 — Enhanced chat feedback (with question/answer)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_feedbacks_v2 (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id TEXT DEFAULT '',
    frage TEXT DEFAULT '',
    antwort TEXT DEFAULT '',
    bewertung TEXT DEFAULT 'positiv',
    fach TEXT DEFAULT '',
    kommentar TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------------------------
-- 50. battle_pass_progress — Battle pass level progress
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS battle_pass_progress (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    season_id INTEGER,
    level INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    claimed_rewards JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- =========================================================================
-- INDEXES (27+ for production performance)
-- =========================================================================

-- Users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_clerk_id ON users(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(subscription_tier);

-- Learning profiles
CREATE INDEX IF NOT EXISTS idx_learning_profiles_user ON learning_profiles(user_id);

-- Chat sessions
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id, updated_at);

-- Quiz results
CREATE INDEX IF NOT EXISTS idx_quiz_results_user ON quiz_results(user_id, completed_at);
CREATE INDEX IF NOT EXISTS idx_quiz_results_subject ON quiz_results(user_id, subject);

-- Activity log
CREATE INDEX IF NOT EXISTS idx_activity_log_user ON activity_log(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_activity_log_type ON activity_log(user_id, activity_type, created_at);

-- Gamification
CREATE INDEX IF NOT EXISTS idx_gamification_user ON gamification(user_id);

-- Tournaments
CREATE INDEX IF NOT EXISTS idx_tournaments_date ON tournaments(date, status);
CREATE INDEX IF NOT EXISTS idx_tournament_entries_user ON tournament_entries(user_id, tournament_id);

-- Daily quests
CREATE INDEX IF NOT EXISTS idx_daily_quests_user ON daily_quests(user_id, quest_date);

-- Notifications
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read, created_at);

-- Spaced repetition
CREATE INDEX IF NOT EXISTS idx_spaced_repetition_review ON spaced_repetition(user_id, next_review);

-- Flashcards
CREATE INDEX IF NOT EXISTS idx_flashcards_review ON flashcards(user_id, next_review);

-- KI relationship
CREATE INDEX IF NOT EXISTS idx_ki_relationship_user ON ki_relationship(user_id);

-- Question history
CREATE INDEX IF NOT EXISTS idx_question_history_user_fach ON question_history(user_id, fach, gesehen_am);

-- Battle pass
CREATE INDEX IF NOT EXISTS idx_battle_pass_user ON battle_pass(user_id);
CREATE INDEX IF NOT EXISTS idx_battle_pass_progress_user ON battle_pass_progress(user_id);

-- XP log
CREATE INDEX IF NOT EXISTS idx_xp_log_user ON xp_log(user_id, created_at);

-- Noten prognose
CREATE INDEX IF NOT EXISTS idx_noten_prognose_user ON noten_prognose(user_id, fach);

-- Schulbuch scans
CREATE INDEX IF NOT EXISTS idx_schulbuch_scans_user ON schulbuch_scans(user_id, created_at);

-- WebSocket tickets
CREATE INDEX IF NOT EXISTS idx_ws_tickets_ticket ON ws_tickets(ticket, expires_at);

-- Quiz confidence
CREATE INDEX IF NOT EXISTS idx_quiz_confidence_user ON quiz_confidence(user_id, fach, blind_spot);

-- Knowledge updates
CREATE INDEX IF NOT EXISTS idx_knowledge_updates_date ON knowledge_updates(created_at);

-- Prompt suggestions
CREATE INDEX IF NOT EXISTS idx_prompt_vorschlaege_status ON prompt_vorschlaege(status);

-- Chat feedbacks v2
CREATE INDEX IF NOT EXISTS idx_chat_feedbacks_v2_fach ON chat_feedbacks_v2(fach, bewertung, created_at);
"""


def print_schema() -> None:
    """Print the PostgreSQL schema to stdout."""
    print(POSTGRES_SCHEMA)


def apply_schema() -> None:
    """Apply the schema to a PostgreSQL database specified by DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        print("Example: DATABASE_URL=postgresql://user:pass@host:5432/lumnos", file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg is not installed. Run: poetry add 'psycopg[binary]'", file=sys.stderr)
        sys.exit(1)

    print("Connecting to PostgreSQL...")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(POSTGRES_SCHEMA)
        conn.commit()
    print("Schema applied successfully — 50 tables + 27 indexes created.")


def migrate_data(sqlite_path: str) -> None:
    """Migrate data from SQLite to PostgreSQL.

    Reads all rows from every table in the SQLite database and inserts them
    into the PostgreSQL database specified by DATABASE_URL.

    Args:
        sqlite_path: Path to the SQLite database file.
    """
    import sqlite3

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg is not installed.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(sqlite_path):
        print(f"ERROR: SQLite file not found: {sqlite_path}", file=sys.stderr)
        sys.exit(1)

    # Table migration order (respects foreign key dependencies)
    TABLE_ORDER = [
        "users",
        "learning_profiles",
        "chat_sessions",
        "quiz_results",
        "learning_resources",
        "quiz_answers",
        "activity_log",
        "user_memories",
        "abitur_simulations",
        "wochen_coach_plans",
        "gamification",
        "group_chats",
        "research_results",
        "coupons",
        "coupon_redemptions",
        "tournaments",
        "tournament_entries",
        "admin_logs",
        "iq_tests",
        "iq_results",
        "chat_feedback",
        "multiplayer_rooms",
        "school_licenses",
        "push_subscriptions",
        "pomodoro_sessions",
        "shop_purchases",
        "challenges_db",
        "challenge_progress",
        "spaced_repetition",
        "daily_quests",
        "parent_links",
        "seasonal_events",
        "ki_relationship",
        "marketplace_items",
        "notifications",
        "flashcards",
        "xp_log",
        "question_history",
        "noten_prognose",
        "battle_pass",
        "parent_link_requests",
        "marketplace_purchases",
        "schulbuch_scans",
        "ws_tickets",
        "quiz_confidence",
        "lehrplan_themen",
        "knowledge_updates",
        "prompt_vorschlaege",
        "chat_feedbacks_v2",
        "battle_pass_progress",
    ]

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    print(f"Migrating data from {sqlite_path} ...")
    total_rows = 0

    with psycopg.connect(database_url) as pg_conn:
        for table_name in TABLE_ORDER:
            try:
                cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
            except sqlite3.OperationalError:
                print(f"  SKIP {table_name} (not in SQLite)")
                continue

            if not rows:
                print(f"  SKIP {table_name} (0 rows)")
                continue

            columns = [desc[0] for desc in cursor.description]
            # Skip 'id' column — let PostgreSQL SERIAL handle it
            non_id_cols = [c for c in columns if c != "id"]
            placeholders = ", ".join(["%s"] * len(non_id_cols))
            col_list = ", ".join(non_id_cols)
            insert_sql = (
                f"INSERT INTO {table_name} ({col_list}) "
                f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            )

            count = 0
            with pg_conn.cursor() as cur:
                for row in rows:
                    values = [row[c] for c in non_id_cols]
                    try:
                        cur.execute(insert_sql, values)
                        count += 1
                    except Exception as e:
                        print(f"  WARN {table_name} row skip: {e}")
            pg_conn.commit()

            total_rows += count
            print(f"  OK   {table_name}: {count} rows migrated")

    sqlite_conn.close()
    print(f"\nDone! {total_rows} total rows migrated across {len(TABLE_ORDER)} tables.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lumnos PostgreSQL migration")
    parser.add_argument("--apply", action="store_true", help="Apply schema to DATABASE_URL")
    parser.add_argument(
        "--migrate-data", action="store_true",
        help="Migrate data from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path", default="./app.db",
        help="Path to SQLite database file (default: ./app.db)"
    )
    args = parser.parse_args()

    if args.migrate_data:
        apply_schema()
        migrate_data(args.sqlite_path)
    elif args.apply:
        apply_schema()
    else:
        print_schema()
