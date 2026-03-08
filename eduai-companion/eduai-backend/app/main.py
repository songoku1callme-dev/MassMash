import os
import logging
import secrets as _secrets
from datetime import datetime, timedelta

# Load .env BEFORE any other imports so os.getenv() works everywhere
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import init_db
from app.core.auth import get_current_user
from app.core.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    BotProtectionMiddleware,
    ALLOWED_ORIGINS,
)
from app.routes import auth, chat, quiz, learning, rag, ocr, admin, memory, abitur, research, gamification, groups, tournaments, iq_test, flashcards, notes, referral, password_reset, calendar, multiplayer, legal, adaptive, school, intelligence, pomodoro, shop, challenges, voice, parents, quests, events, matching, notifications, marketplace, pdf_export, battle_pass, stats, schulbuch, voice_exam, confidence, erklaerung, vision, audio
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
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PR #48: Startup Memory Check
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    try:
        import psutil
        process = psutil.Process(os.getpid())
        startup_ram = process.memory_info().rss / 1024 ** 2
        logger.info("Startup RAM: %.1f MB", startup_ram)
        if startup_ram > 400:
            logger.warning(
                "WARNUNG: Startup RAM %.1f MB > 400 MB! "
                "Ziel ist < 200 MB für 512 MB Free-Tier.",
                startup_ram,
            )
        elif startup_ram > 200:
            logger.info(
                "Startup RAM %.1f MB (über 200 MB Ziel, aber unter 400 MB Limit)",
                startup_ram,
            )
        else:
            logger.info("Startup RAM %.1f MB — optimal für Free-Tier!", startup_ram)
    except Exception as mem_err:
        logger.warning("Memory check fehlgeschlagen: %s", mem_err)

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

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Quality Engine v2 Block 4: Self-Learning Nightly Cron
            # Analysiert negative Feedbacks und verbessert Fach-Prompts
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            scheduler.add_job(
                _nightly_self_learning_job,
                CronTrigger(hour=2, minute=0, timezone=tz_berlin),
                id="self_learning", replace_existing=True,
            )

            # Load approved prompts on startup
            try:
                import asyncio
                asyncio.ensure_future(load_approved_prompts())
                logger.info("Approved prompts werden geladen...")
            except Exception as prompt_err:
                logger.warning("Prompt-Laden fehlgeschlagen: %s", prompt_err)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # PR #45: AUFGABE 2 — APScheduler Automation
            # All Daily/Weekly/Monthly/Hourly jobs
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                from app.services.scheduler import setup_scheduler
                setup_scheduler(scheduler)
                logger.info("AUFGABE 2: Scheduler Jobs registriert")
            except Exception as sched_err:
                logger.warning("Scheduler Setup fehlgeschlagen (non-fatal): %s", sched_err)

            scheduler.start()
            logger.info("Scheduler gestartet: %d Jobs registriert", len(scheduler.get_jobs()))
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


async def _nightly_self_learning_job():
    """Quality Engine v2 Block 4: Self-Learning Nightly Cron.

    Analysiert alle negativ bewerteten Antworten des Tages,
    lässt 70b analysieren warum sie schlecht waren,
    und speichert Verbesserungsvorschläge für Fach-Prompts.
    """
    logger.info("Running nightly self-learning job (Quality Engine v2 Block 4)")
    try:
        import aiosqlite
        import httpx
        db_path = os.getenv("DATABASE_PATH", "app.db")
        groq_key = os.getenv("GROQ_API_KEY", "")

        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Hole alle negativen Feedbacks von heute
            cursor = await db.execute(
                """SELECT cf.session_id, cf.message_index, cf.reason,
                          cs.subject, cs.messages
                FROM chat_feedback cf
                LEFT JOIN chat_sessions cs ON cf.session_id = cs.id
                WHERE cf.rating = 'negative'
                AND DATE(cf.created_at) = DATE('now')
                ORDER BY cf.id DESC
                LIMIT 20"""
            )
            rows = await cursor.fetchall()
            if not rows:
                logger.info("Keine negativen Feedbacks heute — nichts zu lernen.")
                return

            # Sammle Fehler-Muster pro Fach
            fach_fehler: dict[str, list[str]] = {}
            for r in rows:
                rd = dict(r)
                fach = rd.get("subject", "Allgemein") or "Allgemein"
                reason = rd.get("reason", "") or "unbekannt"
                msg_idx = rd.get("message_index", 0)

                # Extrahiere die problematische Antwort
                try:
                    import json as _json
                    msgs = _json.loads(rd.get("messages", "[]"))
                    if msg_idx < len(msgs):
                        antwort = msgs[msg_idx].get("content", "")[:200]
                    else:
                        antwort = ""
                except Exception:
                    antwort = ""

                fehler_text = f"Grund: {reason}"
                if antwort:
                    fehler_text += f" | Antwort-Auszug: {antwort}"
                fach_fehler.setdefault(fach, []).append(fehler_text)

            # Für jedes Fach: 70b analysieren lassen
            if not groq_key:
                logger.warning("GROQ_API_KEY nicht gesetzt — Self-Learning übersprungen")
                return

            for fach, fehler_liste in fach_fehler.items():
                analyse_prompt = (
                    f"Du bist ein Bildungsexperte für das Fach '{fach}'.\n"
                    f"Folgende KI-Antworten wurden von Schülern als schlecht bewertet:\n\n"
                    + "\n".join([f"- {f}" for f in fehler_liste[:10]])
                    + "\n\nAnalysiere die Muster und gib KONKRETE Verbesserungsvorschläge "
                    "für den System-Prompt des Fachs. Maximal 3 Sätze."
                )

                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {groq_key}"},
                            json={
                                "model": "llama-3.3-70b-versatile",
                                "messages": [{"role": "user", "content": analyse_prompt}],
                                "temperature": 0.2,
                                "max_tokens": 300,
                            },
                        )
                        if resp.status_code == 200:
                            analyse = resp.json()["choices"][0]["message"]["content"]
                        else:
                            analyse = f"Groq-API-Fehler: {resp.status_code}"
                except Exception as api_err:
                    analyse = f"API-Fehler: {api_err}"

                # Speichere Verbesserungsvorschlag in DB
                await db.execute(
                    """INSERT OR REPLACE INTO prompt_improvements
                    (fach, verbesserung, fehler_count, created_at)
                    VALUES (?, ?, ?, datetime('now'))""",
                    (fach, analyse, len(fehler_liste)),
                )
                logger.info(
                    "Self-Learning [%s]: %d Fehler analysiert → %s",
                    fach, len(fehler_liste), analyse[:100],
                )

            await db.commit()

            # Erstelle prompt_improvements Tabelle falls nicht vorhanden
            await db.execute(
                """CREATE TABLE IF NOT EXISTS prompt_improvements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fach TEXT NOT NULL,
                    verbesserung TEXT NOT NULL,
                    fehler_count INTEGER DEFAULT 0,
                    applied INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                )"""
            )
            await db.commit()

            logger.info(
                "Self-Learning abgeschlossen: %d Fächer analysiert",
                len(fach_fehler),
            )
    except Exception as exc:
        logger.error("Self-Learning job failed: %s", exc)


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
# Enhanced with Pedagogical Brain Block 5 fixes
ws_tickets: dict[str, dict] = {}


def validate_ws_ticket(ticket: str) -> int | None:
    """Validate a WebSocket ticket and return user_id if valid.

    Returns None if ticket is invalid, expired, or already used.
    Tickets are single-use and expire after 30 seconds.
    """
    if not ticket or ticket not in ws_tickets:
        return None

    ticket_data = ws_tickets[ticket]
    now = datetime.utcnow()

    # Check expiry
    if now > ticket_data["expires"]:
        del ws_tickets[ticket]
        return None

    # Single-use: consume the ticket
    user_id = ticket_data["user_id"]
    del ws_tickets[ticket]

    # Cleanup expired tickets (prevent memory leak)
    expired = [k for k, v in ws_tickets.items() if now > v["expires"]]
    for k in expired:
        del ws_tickets[k]

    return user_id


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


@app.websocket("/ws/{ticket}")
async def websocket_endpoint(websocket, ticket: str):
    """Authenticated WebSocket endpoint for real-time features.

    Validates the ticket before allowing connection.
    Used for: Gruppen-Chats, Live-Quiz, Status-Updates.
    """
    from starlette.websockets import WebSocket, WebSocketDisconnect

    user_id = validate_ws_ticket(ticket)
    if user_id is None:
        await websocket.close(code=4001, reason="Ungültiges oder abgelaufenes Ticket")
        return

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back with user context (extend for specific features)
            await websocket.send_json({
                "type": "ack",
                "user_id": user_id,
                "message": data,
            })
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: user_id=%s", user_id)
    except Exception as e:
        logger.warning("WebSocket error: %s", e)

# --- Security middleware (outermost first) ---
# Shield 10: Bot protection + request size limit
app.add_middleware(BotProtectionMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
# Shield 6: Security headers (CSP, HSTS, X-Frame-Options)
app.add_middleware(SecurityHeadersMiddleware)
# Shield 3: Rate limiting with login lockout
app.add_middleware(RateLimitMiddleware)

# CORS — restrict to known frontend origins in production, allow all in dev
_cors_origins: list[str] = ["*"] if os.getenv("LUMNOS_DEV_MODE") else ALLOWED_ORIGINS
# Regex to match all Vercel preview URLs for this project
_vercel_preview_regex = r"https://mass-mash-[a-z0-9]+-songoku1callme-devs-projects\.vercel\.app"
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_vercel_preview_regex if not os.getenv("LUMNOS_DEV_MODE") else None,
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
app.include_router(erklaerung.router)
app.include_router(vision.router)
app.include_router(audio.router)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PR #46: Keep-Alive Ping Endpoint
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/api/ping")
async def ping():
    """Lightweight keep-alive endpoint (Zero-Budget: prevents sleep on free tiers)."""
    return {"pong": True}


@app.get("/healthz")
async def healthz():
    """Production health check used by Koyeb/Railway and monitoring."""
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
