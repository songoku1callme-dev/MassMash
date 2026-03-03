import os
import logging
import secrets as _secrets
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import init_db
from app.core.auth import get_current_user
from app.core.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    ALLOWED_ORIGINS,
)
from app.routes import auth, chat, quiz, learning, rag, ocr, admin, memory, abitur, research, gamification, groups, tournaments, iq_test, flashcards, notes, referral, password_reset, calendar, multiplayer, legal, adaptive, school, intelligence, pomodoro, shop, challenges, voice, parents, quests, events, matching, notifications, marketplace, pdf_export, battle_pass, stats, schulbuch, voice_exam, confidence
from app.routes import stripe_routes
from app.core.monitoring import init_sentry, init_posthog, shutdown_posthog

logger = logging.getLogger(__name__)


# --- APScheduler for background jobs ---
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    scheduler = AsyncIOScheduler()
    _has_scheduler = True
except ImportError:
    scheduler = None  # type: ignore[assignment]
    _has_scheduler = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database, monitoring and scheduler on startup."""
    init_sentry()
    init_posthog()
    await init_db()

    # Start APScheduler with background jobs
    if _has_scheduler and scheduler is not None:
        try:
            # Daily 20:00 UTC — Streak warning for inactive users
            scheduler.add_job(
                _streak_warning_job, CronTrigger(hour=20, minute=0),
                id="streak_warning", replace_existing=True,
            )
            # Daily 09:00 UTC — Spaced repetition reminders
            scheduler.add_job(
                _spaced_repetition_job, CronTrigger(hour=9, minute=0),
                id="spaced_repetition", replace_existing=True,
            )
            # Monday 08:00 UTC — Weekly report email
            scheduler.add_job(
                _weekly_report_job, CronTrigger(day_of_week="mon", hour=8, minute=0),
                id="weekly_report", replace_existing=True,
            )
            # Daily 18:00 UTC — Auto-create tournament (Phase 8)
            scheduler.add_job(
                _daily_tournament_job, CronTrigger(hour=18, minute=0),
                id="daily_tournament", replace_existing=True,
            )
            # Daily 16:00 UTC — Proactive learning tips (Phase 6)
            scheduler.add_job(
                _proactive_tips_job, CronTrigger(hour=16, minute=0),
                id="proactive_tips", replace_existing=True,
            )
            # Ghost Founder Engine (Block 3)
            from app.services.ghost_founder import (
                send_daily_impulse, check_inactive_users,
                send_weekly_report as ghost_weekly_report,
            )
            scheduler.add_job(
                send_daily_impulse, CronTrigger(hour=8, minute=0),
                id="ghost_daily_impulse", replace_existing=True,
            )
            scheduler.add_job(
                check_inactive_users, CronTrigger(hour=18, minute=0),
                id="ghost_inactivity", replace_existing=True,
            )
            scheduler.add_job(
                ghost_weekly_report, CronTrigger(day_of_week="sun", hour=20, minute=0),
                id="ghost_weekly_report", replace_existing=True,
            )

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Self-Evolution Jobs (Fix 2)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            import pytz
            tz_berlin = pytz.timezone("Europe/Berlin")

            # Nightly Deep Crawl — 03:00 Berlin
            from app.services.deep_crawler import nightly_knowledge_update
            scheduler.add_job(
                nightly_knowledge_update,
                CronTrigger(hour=3, minute=0, timezone=tz_berlin),
                id="nightly_crawl", replace_existing=True,
            )

            # Weekly Prompt Optimization — Montag 04:00 Berlin
            from app.services.prompt_optimizer import (
                weekly_prompt_optimization, load_approved_prompts,
            )
            scheduler.add_job(
                weekly_prompt_optimization,
                CronTrigger(day_of_week="mon", hour=4, minute=0, timezone=tz_berlin),
                id="prompt_optimization", replace_existing=True,
            )

            # Load approved prompts on startup
            try:
                import asyncio
                asyncio.ensure_future(load_approved_prompts())
                logger.info("Approved prompts werden geladen...")
            except Exception as prompt_err:
                logger.warning("Prompt-Laden fehlgeschlagen: %s", prompt_err)

            scheduler.start()
            logger.info("✅ Scheduler gestartet: %d Jobs registriert", len(scheduler.get_jobs()))
        except Exception as exc:
            logger.warning("APScheduler start failed (non-fatal): %s", exc)

    yield

    if _has_scheduler and scheduler is not None:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass
    shutdown_posthog()


# --- Scheduled job implementations (Supreme 12.0) ---
async def _streak_warning_job():
    """Notify users with streak >= 3 who haven't been active today."""
    logger.info("Running streak warning job")
    try:
        import aiosqlite
        from app.services.email_service import send_streak_loss_email
        db_path = os.getenv("DATABASE_PATH", "app.db")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, username, email, streak_days FROM users
                WHERE streak_days >= 3
                AND DATE(last_active) < DATE('now')
                AND email IS NOT NULL AND email != ''"""
            )
            users = await cursor.fetchall()
            for u in users:
                ud = dict(u)
                await send_streak_loss_email(
                    ud["email"], ud["username"], ud["streak_days"]
                )
                # Reset streak
                await db.execute(
                    "UPDATE users SET streak_days = 0 WHERE id = ?", (ud["id"],)
                )
            await db.commit()
            logger.info("Streak warnings sent to %d users", len(users))
    except Exception as exc:
        logger.error("Streak warning job failed: %s", exc)


async def _spaced_repetition_job():
    """Send spaced repetition reminders for due reviews."""
    logger.info("Running spaced repetition job")
    try:
        import aiosqlite
        db_path = os.getenv("DATABASE_PATH", "app.db")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            # Create notifications for users with due flashcards
            cursor = await db.execute(
                """SELECT DISTINCT user_id FROM flashcards
                WHERE next_review <= datetime('now')"""
            )
            users = await cursor.fetchall()
            for u in users:
                uid = dict(u)["user_id"]
                await db.execute(
                    """INSERT INTO notifications (user_id, title, message, notification_type)
                    VALUES (?, 'Wiederholung fällig', 'Du hast Karteikarten die wiederholt werden müssen!', 'reminder')""",
                    (uid,),
                )
            await db.commit()
            logger.info("Spaced repetition reminders for %d users", len(users))
    except Exception as exc:
        logger.error("Spaced repetition job failed: %s", exc)


async def _weekly_report_job():
    """Send weekly learning report emails (Monday 08:00 UTC)."""
    logger.info("Running weekly report job")
    try:
        import aiosqlite
        from app.services.email_service import send_weekly_report_email
        db_path = os.getenv("DATABASE_PATH", "app.db")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, username, email, streak_days FROM users WHERE email IS NOT NULL AND email != ''"
            )
            users = await cursor.fetchall()
            for u in users:
                ud = dict(u)
                # Get weekly stats
                qc = await db.execute(
                    """SELECT COUNT(*) as cnt, AVG(score) as avg FROM quiz_results
                    WHERE user_id = ? AND created_at >= date('now', '-7 days')""",
                    (ud["id"],),
                )
                qr = await qc.fetchone()
                qd = dict(qr) if qr else {}
                stats = {
                    "total_xp": 0,
                    "streak_days": ud.get("streak_days", 0),
                    "week_quizzes": qd.get("cnt", 0) or 0,
                    "avg_quiz_score": round(qd.get("avg", 0) or 0),
                    "week_learning_minutes": 0,
                }
                await send_weekly_report_email(ud["email"], ud["username"], stats)
            logger.info("Weekly reports sent to %d users", len(users))
    except Exception as exc:
        logger.error("Weekly report job failed: %s", exc)


async def _daily_tournament_job():
    """Create daily tournament at 18:00 UTC (Supreme 12.0 Phase 8)."""
    logger.info("Running daily tournament creation job")
    try:
        import aiosqlite
        from app.routes.tournaments import create_daily_tournament
        db_path = os.getenv("DATABASE_PATH", "app.db")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            result = await create_daily_tournament(db)
            logger.info("Daily tournament created: %s", result.get("subject", "unknown"))
    except Exception as exc:
        logger.error("Daily tournament job failed: %s", exc)


async def _proactive_tips_job():
    """Send proactive learning tips at 16:00 UTC (Supreme 12.0 Phase 6)."""
    logger.info("Running proactive tips job")
    try:
        import aiosqlite
        db_path = os.getenv("DATABASE_PATH", "app.db")
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            # Get active users from last 3 days
            cursor = await db.execute(
                """SELECT DISTINCT user_id FROM activity_log
                WHERE created_at >= date('now', '-3 days')"""
            )
            users = await cursor.fetchall()
            tips = [
                "Tipp: Wiederhole heute dein schwächstes Fach!",
                "Tipp: Ein kurzes Quiz hilft beim Merken!",
                "Tipp: Probiere den IQ-Test für neue Herausforderungen!",
                "Tipp: Nimm am Turnier teil und gewinne XP!",
                "Tipp: Erstelle Karteikarten für effektives Lernen!",
            ]
            import random
            for u in users:
                uid = dict(u)["user_id"]
                tip = random.choice(tips)
                await db.execute(
                    """INSERT INTO notifications (user_id, title, message, notification_type)
                    VALUES (?, 'Lern-Tipp', ?, 'tip')""",
                    (uid, tip),
                )
            await db.commit()
            logger.info("Proactive tips sent to %d users", len(users))
    except Exception as exc:
        logger.error("Proactive tips job failed: %s", exc)


app = FastAPI(
    title="Lumnos Companion",
    description="AI-powered tutoring for German students",
    version="1.0.0",
    lifespan=lifespan
)

# --- Perfect School 4.1: WebSocket Ticket System (Block 1.3) ---
ws_tickets: dict[str, dict] = {}


@app.post("/api/ws/ticket")
async def get_ws_ticket(current_user: dict = Depends(get_current_user)):
    """Issue a short-lived ticket for WebSocket authentication.

    The ticket expires after 30 seconds and can only be used once.
    This avoids passing the JWT in the WebSocket URL path.
    """
    ticket = _secrets.token_urlsafe(32)
    ws_tickets[ticket] = {
        "user_id": current_user["id"],
        "expires": datetime.utcnow() + timedelta(seconds=30),
    }
    return {"ticket": ticket}

# --- Security middleware (outermost first) ---
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS — restrict to known frontend origins in production, allow all in dev
_cors_origins: list[str] = ["*"] if os.getenv("LUMNOS_DEV_MODE") else ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(learning.router)
app.include_router(rag.router)
app.include_router(ocr.router)
app.include_router(admin.router)
app.include_router(memory.router)
app.include_router(abitur.router)
app.include_router(research.router)
app.include_router(stripe_routes.router)
app.include_router(gamification.router)
app.include_router(groups.router)
app.include_router(tournaments.router)
app.include_router(iq_test.router)
app.include_router(flashcards.router)
app.include_router(notes.router)
app.include_router(referral.router)
app.include_router(password_reset.router)
app.include_router(calendar.router)
app.include_router(multiplayer.router)
app.include_router(legal.router)
app.include_router(adaptive.router)
app.include_router(school.router)
app.include_router(intelligence.router)
app.include_router(pomodoro.router)
app.include_router(shop.router)
app.include_router(challenges.router)
app.include_router(voice.router)
app.include_router(parents.router)
app.include_router(quests.router)
app.include_router(events.router)
app.include_router(matching.router)
app.include_router(notifications.router)
app.include_router(marketplace.router)
app.include_router(pdf_export.router)
app.include_router(battle_pass.router)
app.include_router(stats.router)
app.include_router(schulbuch.router)
app.include_router(voice_exam.router)
app.include_router(confidence.router)


@app.get("/healthz")
async def healthz():
    """Production health check used by Fly.io and monitoring."""
    import time

    checks: dict[str, str] = {}
    # DB connectivity
    try:
        import aiosqlite

        db_path = os.getenv("DATABASE_PATH", "app.db")
        async with aiosqlite.connect(db_path) as db:
            await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {
        "status": overall,
        "version": app.version,
        "checks": checks,
        "timestamp": int(time.time()),
    }
