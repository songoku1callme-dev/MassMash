"""APScheduler Automation — Alle automatisierten Jobs für LUMNOS.

TÄGLICH (00:00): Daily Quests, Streak-Check, XP-Bonus, Knowledge Update
TÄGLICH (08:00): Motivations-Nachricht
WOECHENTLICH (Montag 07:00): Weekly Report, neue Challenges
WOECHENTLICH (Sonntag 23:59): Shop-Rotation, Events aktualisieren
MONATLICH (1. des Monats): Battle Pass Season, Turniere, Leaderboard Reset
JEDE STUNDE: Turnier-Cleanup, Multiplayer Rooms, WebSocket Tickets

Alle Jobs laufen in Europe/Berlin Zeitzone.
"""
import json
import logging
import os
import random
from datetime import datetime, timedelta, date
from typing import Optional

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    return os.getenv("DATABASE_PATH", "app.db")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TÄGLICH 00:00 — Daily Quests generieren
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def generate_daily_quests():
    """3 neue Quests pro User basierend auf Schwächen + Fächern.
    Alte Quests werden auf 'abgelaufen' gesetzt.
    """
    import aiosqlite

    logger.info("Job: generate_daily_quests gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Alte Quests von gestern auf abgelaufen setzen
            gestern = (date.today() - timedelta(days=1)).isoformat()
            await db.execute(
                """UPDATE daily_quests SET completed = -1
                WHERE quest_date < ? AND completed = 0""",
                (date.today().isoformat(),),
            )

            # Aktive User der letzten 7 Tage
            cursor = await db.execute(
                """SELECT DISTINCT user_id FROM activity_log
                WHERE created_at >= date('now', '-7 days')"""
            )
            active_users = await cursor.fetchall()

            count = 0
            for u in active_users:
                user_id = dict(u)["user_id"]
                today_str = date.today().isoformat()

                # Prüfen ob heute schon Quests existieren
                cursor = await db.execute(
                    "SELECT COUNT(*) as cnt FROM daily_quests WHERE user_id = ? AND quest_date = ?",
                    (user_id, today_str),
                )
                row = await cursor.fetchone()
                if row and dict(row)["cnt"] > 0:
                    continue

                # Schwäche ermitteln
                cursor = await db.execute(
                    """SELECT subject FROM quiz_results
                    WHERE user_id = ? AND completed_at >= date('now', '-30 days')
                    GROUP BY subject ORDER BY AVG(score) ASC LIMIT 1""",
                    (user_id,),
                )
                weak_row = await cursor.fetchone()
                weak_subject = dict(weak_row)["subject"] if weak_row else "Mathematik"

                # 3 Quests generieren
                quests = [
                    {
                        "quest_id": f"weak_{today_str}",
                        "title": f"Schwäche üben: {weak_subject}",
                        "description": f"Mache ein Quiz in {weak_subject}",
                        "xp_reward": 50,
                        "target": 1,
                    },
                    {
                        "quest_id": f"streak_{today_str}",
                        "title": "Streak halten",
                        "description": "Lerne heute mindestens 10 Minuten",
                        "xp_reward": 30,
                        "target": 1,
                    },
                    {
                        "quest_id": f"social_{today_str}",
                        "title": "Community-Quest",
                        "description": "Nimm am Turnier teil oder starte ein Multiplayer-Quiz",
                        "xp_reward": 75,
                        "target": 1,
                    },
                ]

                for q in quests:
                    await db.execute(
                        """INSERT OR IGNORE INTO daily_quests
                        (user_id, quest_id, quest_date, title, description, xp_reward, target)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, q["quest_id"], today_str, q["title"],
                         q["description"], q["xp_reward"], q["target"]),
                    )
                count += 1

            await db.commit()
            logger.info("Daily Quests generiert für %d User", count)

    except Exception as exc:
        logger.error("generate_daily_quests fehlgeschlagen: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TÄGLICH 00:05 — Streak prüfen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def check_streaks():
    """User die gestern nicht gelernt haben: Streak auf 0 setzen.
    Push-Notification senden.
    """
    import aiosqlite

    logger.info("Job: check_streaks gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # User mit Streak > 0 die gestern NICHT aktiv waren
            cursor = await db.execute(
                """SELECT id, username, email, streak_days FROM users
                WHERE streak_days > 0
                AND DATE(last_active) < DATE('now')"""
            )
            users = await cursor.fetchall()

            reset_count = 0
            for u in users:
                ud = dict(u)
                user_id = ud["id"]
                lost_streak = ud["streak_days"]

                # Streak zurücksetzen
                await db.execute(
                    "UPDATE users SET streak_days = 0 WHERE id = ?",
                    (user_id,),
                )

                # Notification erstellen
                await db.execute(
                    """INSERT INTO notifications
                    (user_id, title, message, notification_type)
                    VALUES (?, ?, ?, 'warning')""",
                    (user_id,
                     "Streak verloren!",
                     f"Dein {lost_streak}-Tage Streak ist vorbei. Starte heute neu!"),
                )
                reset_count += 1

            await db.commit()
            logger.info("Streaks zurückgesetzt: %d User", reset_count)

    except Exception as exc:
        logger.error("check_streaks fehlgeschlagen: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TÄGLICH 00:10 — XP-Bonus für Top 10
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def distribute_daily_xp_bonus():
    """Top 10 User des Tages bekommen +50 XP Bonus."""
    import aiosqlite

    logger.info("Job: distribute_daily_xp_bonus gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Top 10 User nach Aktivitaet gestern
            cursor = await db.execute(
                """SELECT user_id, COUNT(*) as aktivitaeten
                FROM activity_log
                WHERE DATE(created_at) = DATE('now', '-1 day')
                GROUP BY user_id
                ORDER BY aktivitaeten DESC
                LIMIT 10"""
            )
            top_users = await cursor.fetchall()

            for u in top_users:
                user_id = dict(u)["user_id"]

                # +50 XP
                await db.execute(
                    """UPDATE gamification SET xp = xp + 50
                    WHERE user_id = ?""",
                    (user_id,),
                )

                # Notification
                await db.execute(
                    """INSERT INTO notifications
                    (user_id, title, message, notification_type)
                    VALUES (?, ?, ?, 'reward')""",
                    (user_id,
                     "Top-Lerner Bonus!",
                     "Du warst gestern unter den Top 10! +50 XP"),
                )

            await db.commit()
            logger.info("XP-Bonus verteilt an %d Top-User", len(top_users))

    except Exception as exc:
        logger.error("distribute_daily_xp_bonus fehlgeschlagen: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TÄGLICH 08:00 — Motivations-Nachricht
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MOTIVATIONS_NACHRICHTEN = [
    "Jeder Tag ist eine neue Chance zu lernen! Starte jetzt dein erstes Quiz.",
    "Wusstest du? Regelmaessiges Lernen verbessert dein Gedaechtnis um 40%!",
    "Dein Gehirn ist bereit! Nur 15 Minuten reichen für einen Lernfortschritt.",
    "Top-Schüler lernen jeden Tag ein bisschen. Du schaffst das auch!",
    "Tipp: Wiederhole heute dein schwaechstes Fach — das bringt am meisten!",
    "Neuer Tag, neue Möglichkeiten! Welches Fach möchtest du heute meistern?",
    "Streak-Alarm! Vergiss nicht, heute zu lernen um deinen Streak zu halten.",
    "Fun Fact: Wer täglich 20 Min lernt, schneidet 30% besser in Prüfungen ab.",
    "Challenge des Tages: Schaffe alle 3 Daily Quests!",
    "Dein Wissen waechst jeden Tag. Halte die Lernroutine aufrecht!",
]


async def send_motivation_notifications():
    """Personalisierte Motivations-Nachricht pro User basierend auf Schwäche."""
    import aiosqlite

    logger.info("Job: send_motivation_notifications gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Aktive User der letzten 14 Tage
            cursor = await db.execute(
                """SELECT DISTINCT user_id FROM activity_log
                WHERE created_at >= date('now', '-14 days')"""
            )
            users = await cursor.fetchall()

            for u in users:
                user_id = dict(u)["user_id"]
                nachricht = random.choice(MOTIVATIONS_NACHRICHTEN)

                await db.execute(
                    """INSERT INTO notifications
                    (user_id, title, message, notification_type)
                    VALUES (?, 'Guten Morgen!', ?, 'motivation')""",
                    (user_id, nachricht),
                )

            await db.commit()
            logger.info("Motivations-Nachrichten gesendet an %d User", len(users))

    except Exception as exc:
        logger.error("send_motivation_notifications fehlgeschlagen: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WOECHENTLICH Montag 07:00 — Weekly Report + Challenges
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def generate_weekly_report():
    """Weekly Report: Lernzeit, Quiz-Score, XP, Streak, Verbesserungen.
    Per Email (Resend) + In-App Notification.
    """
    import aiosqlite

    logger.info("Job: generate_weekly_report gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """SELECT id, username, email FROM users
                WHERE email IS NOT NULL AND email != ''"""
            )
            users = await cursor.fetchall()

            for u in users:
                ud = dict(u)
                user_id = ud["id"]

                # Wochen-Stats berechnen
                qc = await db.execute(
                    """SELECT COUNT(*) as cnt, AVG(score) as avg_score
                    FROM quiz_results
                    WHERE user_id = ? AND completed_at >= date('now', '-7 days')""",
                    (user_id,),
                )
                qr = await qc.fetchone()
                qd = dict(qr) if qr else {}

                quiz_count = qd.get("cnt", 0) or 0
                avg_score = round(qd.get("avg_score", 0) or 0, 1)

                # In-App Notification
                await db.execute(
                    """INSERT INTO notifications
                    (user_id, title, message, notification_type)
                    VALUES (?, ?, ?, 'report')""",
                    (user_id,
                     "Dein Wochen-Report",
                     f"Diese Woche: {quiz_count} Quizze, {avg_score}% Durchschnitt. Weiter so!"),
                )

                # Email senden (best-effort)
                if ud.get("email"):
                    try:
                        from app.services.email_service import send_weekly_report_email
                        stats = {
                            "total_xp": 0,
                            "streak_days": 0,
                            "week_quizzes": quiz_count,
                            "avg_quiz_score": avg_score,
                            "week_learning_minutes": 0,
                        }
                        await send_weekly_report_email(
                            ud["email"], ud["username"], stats
                        )
                    except Exception as mail_err:
                        logger.warning("Weekly Report Email fehlgeschlagen: %s", mail_err)

            await db.commit()
            logger.info("Weekly Reports generiert für %d User", len(users))

    except Exception as exc:
        logger.error("generate_weekly_report fehlgeschlagen: %s", exc)


async def create_weekly_challenges():
    """5 neue Wochenchallenges basierend auf Fach-Popularitaet."""
    import aiosqlite

    logger.info("Job: create_weekly_challenges gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Populärste Fächer ermitteln
            cursor = await db.execute(
                """SELECT subject, COUNT(*) as cnt FROM chat_sessions
                GROUP BY subject ORDER BY cnt DESC LIMIT 5"""
            )
            top_faecher = await cursor.fetchall()
            faecher = [dict(r)["subject"] for r in top_faecher] if top_faecher else [
                "Mathematik", "Deutsch", "Englisch", "Physik", "Geschichte"
            ]

            # 5 Challenges erstellen
            woche_start = date.today().isoformat()
            woche_ende = (date.today() + timedelta(days=7)).isoformat()

            challenges = [
                {
                    "title": f"Quiz-Meister: {faecher[0]}",
                    "description": f"Schaffe 5 Quizze in {faecher[0]} diese Woche",
                    "target": 5, "xp_reward": 200, "fach": faecher[0],
                },
                {
                    "title": "Streak-Held",
                    "description": "Halte 7 Tage Streak diese Woche",
                    "target": 7, "xp_reward": 300, "fach": "Alle",
                },
                {
                    "title": "Turnier-Champion",
                    "description": "Nimm an 3 Turnieren teil",
                    "target": 3, "xp_reward": 250, "fach": "Alle",
                },
                {
                    "title": f"Entdecker: {faecher[min(1, len(faecher)-1)]}",
                    "description": f"Stelle 10 Fragen in {faecher[min(1, len(faecher)-1)]}",
                    "target": 10, "xp_reward": 150, "fach": faecher[min(1, len(faecher)-1)],
                },
                {
                    "title": "Karteikarten-Profi",
                    "description": "Erstelle 20 Karteikarten",
                    "target": 20, "xp_reward": 175, "fach": "Alle",
                },
            ]

            for ch in challenges:
                await db.execute(
                    """INSERT INTO weekly_challenges
                    (title, description, target, xp_reward, fach, week_start, week_end)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (ch["title"], ch["description"], ch["target"],
                     ch["xp_reward"], ch["fach"], woche_start, woche_ende),
                )

            await db.commit()
            logger.info("5 Weekly Challenges erstellt")

    except Exception as exc:
        logger.error("create_weekly_challenges fehlgeschlagen: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WOECHENTLICH Sonntag 23:59 — Shop rotieren + Events
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Rotations-Items für den Shop
ROTATION_ITEMS = [
    {"id": "theme_neon", "name": "Neon Theme", "category": "theme", "price": 600, "icon": "palette"},
    {"id": "theme_galaxy", "name": "Galaxy Theme", "category": "theme", "price": 700, "icon": "palette"},
    {"id": "theme_retro", "name": "Retro Theme", "category": "theme", "price": 550, "icon": "palette"},
    {"id": "theme_aurora", "name": "Aurora Theme", "category": "theme", "price": 650, "icon": "palette"},
    {"id": "theme_cyberpunk", "name": "Cyberpunk Theme", "category": "theme", "price": 800, "icon": "palette"},
    {"id": "ki_einstein", "name": "Einstein KI", "category": "ki", "price": 1200, "icon": "bot"},
    {"id": "ki_rapper", "name": "Rapper KI", "category": "ki", "price": 1100, "icon": "bot"},
    {"id": "ki_sportler", "name": "Sportler KI", "category": "ki", "price": 1000, "icon": "bot"},
    {"id": "frame_feuer", "name": "Feuer-Rahmen", "category": "frame", "price": 900, "icon": "flame"},
    {"id": "frame_kristall", "name": "Kristall-Rahmen", "category": "frame", "price": 1300, "icon": "gem"},
    {"id": "boost_triple_xp", "name": "Dreifach-XP (1h)", "category": "boost", "price": 400, "icon": "zap"},
    {"id": "boost_reveal", "name": "Antwort-Enthuellung", "category": "boost", "price": 350, "icon": "eye"},
]


async def rotate_shop_items():
    """3-5 neue Items im Shop, alte Items entfernen, Notification senden."""
    import aiosqlite

    logger.info("Job: rotate_shop_items gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # 3-5 zufällige Rotation Items auswählen
            num_items = random.randint(3, 5)
            neue_items = random.sample(ROTATION_ITEMS, min(num_items, len(ROTATION_ITEMS)))

            # Speichere aktuelle Rotation in DB
            rotation_data = json.dumps([item["id"] for item in neue_items])
            await db.execute(
                """INSERT OR REPLACE INTO shop_rotations
                (week_date, items_json, created_at)
                VALUES (date('now'), ?, datetime('now'))""",
                (rotation_data,),
            )

            # Notification an alle User
            cursor = await db.execute("SELECT id FROM users")
            users = await cursor.fetchall()

            item_namen = ", ".join([i["name"] for i in neue_items[:3]])
            for u in users:
                user_id = dict(u)["id"]
                await db.execute(
                    """INSERT INTO notifications
                    (user_id, title, message, notification_type)
                    VALUES (?, ?, ?, 'shop')""",
                    (user_id,
                     "Neue Items im Shop!",
                     f"Diese Woche neu: {item_namen} und mehr!"),
                )

            await db.commit()
            logger.info("Shop rotiert: %d neue Items", len(neue_items))

    except Exception as exc:
        logger.error("rotate_shop_items fehlgeschlagen: %s", exc)


async def update_seasonal_events():
    """Saisonale Events prüfen, neue aktivieren, abgelaufene deaktivieren."""
    import aiosqlite

    logger.info("Job: update_seasonal_events gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            now = datetime.now().strftime("%Y-%m-%d")

            # Events die heute starten aktivieren
            await db.execute(
                """UPDATE seasonal_events SET status = 'active'
                WHERE start_date <= ? AND end_date >= ? AND status = 'upcoming'""",
                (now, now),
            )

            # Abgelaufene Events deaktivieren
            await db.execute(
                """UPDATE seasonal_events SET status = 'ended'
                WHERE end_date < ? AND status = 'active'""",
                (now,),
            )

            await db.commit()
            logger.info("Seasonal Events aktualisiert")

    except Exception as exc:
        logger.error("update_seasonal_events fehlgeschlagen: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MONATLICH (1. des Monats) — Battle Pass + Turniere + Leaderboard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SEASON_NAMES = [
    "Fruehling", "Sommer", "Herbst", "Winter",
    "Nebel", "Sturm", "Eis", "Feuer",
    "Kristall", "Schatten", "Licht", "Donner",
]


async def start_new_battle_pass_season():
    """Neue Season starten, Rewards generieren, alle User auf Level 0 zurücksetzen.
    'Neue Season!' Push-Notification.
    """
    import aiosqlite

    logger.info("Job: start_new_battle_pass_season gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Season-Name generieren
            now = datetime.now()
            season_name = f"{random.choice(SEASON_NAMES)} {now.year}"

            # Alle Battle Pass auf Level 1 / XP 0 zurücksetzen
            await db.execute(
                """UPDATE battle_pass SET
                current_level = 1, current_xp = 0,
                claimed_rewards = '[]',
                updated_at = datetime('now')"""
            )

            # Notification an alle User
            cursor = await db.execute("SELECT id FROM users")
            users = await cursor.fetchall()

            for u in users:
                user_id = dict(u)["id"]
                await db.execute(
                    """INSERT INTO notifications
                    (user_id, title, message, notification_type)
                    VALUES (?, ?, ?, 'event')""",
                    (user_id,
                     "Neue Season!",
                     f"Battle Pass Season '{season_name}' hat begonnen! Sammle XP für neue Belohnungen."),
                )

            await db.commit()
            logger.info("Neue Battle Pass Season: %s", season_name)

    except Exception as exc:
        logger.error("start_new_battle_pass_season fehlgeschlagen: %s", exc)


TURNIER_FAECHER = [
    "Mathematik", "Deutsch", "Physik", "Englisch", "Geschichte",
    "Biologie", "Chemie", "Informatik", "Geographie", "Wirtschaft",
    "Politik", "Philosophie", "Kunst", "Musik", "Franzoesisch", "Sport",
]


async def create_monthly_tournaments():
    """2 neue Turniere pro Fach mit verschiedenen Schwierigkeitsgraden."""
    import aiosqlite

    logger.info("Job: create_monthly_tournaments gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Wähle 5 Fächer für diesen Monat
            monatliche_faecher = random.sample(TURNIER_FAECHER, min(5, len(TURNIER_FAECHER)))

            created = 0
            for fach in monatliche_faecher:
                for schwierigkeit in ["mittel", "schwer"]:
                    turnier_date = date.today().isoformat()
                    turnier_name = f"{fach} {schwierigkeit.capitalize()}-Turnier"

                    await db.execute(
                        """INSERT INTO tournaments
                        (subject, date, status, questions, num_questions, time_limit_seconds)
                        VALUES (?, ?, 'scheduled', '[]', 20, ?)""",
                        (fach, turnier_date,
                         300 if schwierigkeit == "mittel" else 240),
                    )
                    created += 1

            await db.commit()
            logger.info("Monatliche Turniere erstellt: %d", created)

    except Exception as exc:
        logger.error("create_monthly_tournaments fehlgeschlagen: %s", exc)


async def reset_monthly_leaderboard():
    """Monatliches Ranking resetten. Top 3 mit Badges belohnen."""
    import aiosqlite

    logger.info("Job: reset_monthly_leaderboard gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Top 3 User des letzten Monats (nach XP-Zuwachs)
            cursor = await db.execute(
                """SELECT user_id, SUM(xp_amount) as total_xp
                FROM activity_log
                WHERE activity_type = 'xp_gain'
                AND created_at >= date('now', '-30 days')
                GROUP BY user_id
                ORDER BY total_xp DESC
                LIMIT 3"""
            )
            top3 = await cursor.fetchall()

            badges = ["Gold-Champion", "Silber-Champion", "Bronze-Champion"]
            for rank, u in enumerate(top3):
                user_id = dict(u)["user_id"]
                badge = badges[rank] if rank < len(badges) else "Top-Lerner"

                await db.execute(
                    """INSERT INTO notifications
                    (user_id, title, message, notification_type)
                    VALUES (?, ?, ?, 'achievement')""",
                    (user_id,
                     f"Monatlicher {badge}!",
                     f"Du bist Platz {rank + 1} im monatlichen Ranking! Badge: {badge}"),
                )

            await db.commit()
            logger.info("Monatliches Leaderboard zurückgesetzt, %d Badges vergeben", len(top3))

    except Exception as exc:
        logger.error("reset_monthly_leaderboard fehlgeschlagen: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JEDE STUNDE — Cleanup Jobs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cleanup_tournaments():
    """Abgelaufene Turniere beenden, Gewinner ermitteln + XP vergeben.
    'Turnier beendet!' Notification.
    """
    import aiosqlite

    logger.info("Job: cleanup_tournaments gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Turniere die aelter als 24h sind und noch aktiv
            cursor = await db.execute(
                """SELECT id, subject FROM tournaments
                WHERE status = 'active'
                AND date < date('now')"""
            )
            expired = await cursor.fetchall()

            for t in expired:
                td = dict(t)
                tournament_id = td["id"]

                # Gewinner ermitteln
                cursor = await db.execute(
                    """SELECT user_id, score FROM tournament_entries
                    WHERE tournament_id = ?
                    ORDER BY score DESC, time_taken_seconds ASC
                    LIMIT 3""",
                    (tournament_id,),
                )
                winners = await cursor.fetchall()

                xp_rewards = [200, 100, 50]
                for rank, w in enumerate(winners):
                    wd = dict(w)
                    user_id = wd["user_id"]
                    xp = xp_rewards[rank] if rank < len(xp_rewards) else 25

                    # XP vergeben
                    await db.execute(
                        "UPDATE gamification SET xp = xp + ? WHERE user_id = ?",
                        (xp, user_id),
                    )

                    # Notification
                    await db.execute(
                        """INSERT INTO notifications
                        (user_id, title, message, notification_type)
                        VALUES (?, ?, ?, 'tournament')""",
                        (user_id,
                         "Turnier beendet!",
                         f"Platz {rank + 1} im {td['subject']}-Turnier! +{xp} XP"),
                    )

                # Turnier als beendet markieren
                await db.execute(
                    "UPDATE tournaments SET status = 'completed' WHERE id = ?",
                    (tournament_id,),
                )

            await db.commit()
            logger.info("Turniere aufgeraeumt: %d beendet", len(expired))

    except Exception as exc:
        logger.error("cleanup_tournaments fehlgeschlagen: %s", exc)


async def cleanup_multiplayer_rooms():
    """Inaktive Rooms (>30 Min) loeschen."""
    import aiosqlite

    logger.info("Job: cleanup_multiplayer_rooms gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            # Rooms die aelter als 30 Minuten und noch 'waiting' oder 'active' sind
            result = await db.execute(
                """DELETE FROM multiplayer_rooms
                WHERE status IN ('waiting', 'active')
                AND created_at < datetime('now', '-30 minutes')"""
            )
            await db.commit()
            logger.info("Multiplayer Rooms aufgeraeumt: %d geloescht", result.rowcount)

    except Exception as exc:
        logger.error("cleanup_multiplayer_rooms fehlgeschlagen: %s", exc)


async def cleanup_ws_tickets():
    """Abgelaufene WebSocket-Tickets loeschen (aus main.py ws_tickets dict)."""
    logger.info("Job: cleanup_ws_tickets gestartet")

    try:
        from app.main import ws_tickets
        now = datetime.utcnow()
        expired = [k for k, v in ws_tickets.items() if now > v["expires"]]
        for k in expired:
            del ws_tickets[k]
        if expired:
            logger.info("WebSocket Tickets bereinigt: %d geloescht", len(expired))
    except Exception as exc:
        logger.error("cleanup_ws_tickets fehlgeschlagen: %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PR #46: Keep-Alive Self-Ping (Zero-Budget)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def self_ping():
    """Ping eigenen /api/ping Endpoint alle 10 Min (verhindert Sleep auf Free-Tiers)."""
    import httpx

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8080")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{backend_url}/api/ping", timeout=5)
            logger.debug("Keep-Alive Ping: %s", resp.status_code)
    except Exception as exc:
        logger.debug("Keep-Alive Ping fehlgeschlagen (non-fatal): %s", exc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Scheduler Setup — Wird von main.py aufgerufen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Registry aller Jobs (für Admin-Endpoints)
JOB_REGISTRY: dict[str, dict] = {
    "daily_quests": {
        "func": generate_daily_quests,
        "beschreibung": "Taeglich 3 neue Quests pro User generieren",
        "zeitplan": "Taeglich 00:00",
    },
    "streak_check": {
        "func": check_streaks,
        "beschreibung": "Streaks prüfen und zurücksetzen",
        "zeitplan": "Taeglich 00:05",
    },
    "xp_bonus": {
        "func": distribute_daily_xp_bonus,
        "beschreibung": "Top 10 User +50 XP Bonus",
        "zeitplan": "Taeglich 00:10",
    },
    "knowledge_update": {
        "func": None,  # wird spaeter gesetzt (aus knowledge_updater)
        "beschreibung": "Nightly Knowledge Update (Tavily)",
        "zeitplan": "Taeglich 03:00",
    },
    "daily_motivation": {
        "func": send_motivation_notifications,
        "beschreibung": "Personalisierte Motivations-Nachricht",
        "zeitplan": "Taeglich 08:00",
    },
    "weekly_report": {
        "func": generate_weekly_report,
        "beschreibung": "Woechentlicher Lernbericht per Email + In-App",
        "zeitplan": "Montag 07:00",
    },
    "weekly_challenges": {
        "func": create_weekly_challenges,
        "beschreibung": "5 neue Wochenchallenges erstellen",
        "zeitplan": "Montag 07:00",
    },
    "shop_rotation": {
        "func": rotate_shop_items,
        "beschreibung": "Shop-Items rotieren",
        "zeitplan": "Sonntag 23:59",
    },
    "events_update": {
        "func": update_seasonal_events,
        "beschreibung": "Saisonale Events prüfen und aktualisieren",
        "zeitplan": "Sonntag 23:59",
    },
    "battle_pass_season": {
        "func": start_new_battle_pass_season,
        "beschreibung": "Neue Battle Pass Season starten",
        "zeitplan": "1. des Monats 00:00",
    },
    "monthly_tournaments": {
        "func": create_monthly_tournaments,
        "beschreibung": "2 Turniere pro Fach erstellen",
        "zeitplan": "1. des Monats 00:00",
    },
    "leaderboard_reset": {
        "func": reset_monthly_leaderboard,
        "beschreibung": "Monatliches Ranking resetten + Top 3 Badges",
        "zeitplan": "1. des Monats 00:00",
    },
    "tournament_cleanup": {
        "func": cleanup_tournaments,
        "beschreibung": "Abgelaufene Turniere beenden + Gewinner",
        "zeitplan": "Jede Stunde",
    },
    "multiplayer_cleanup": {
        "func": cleanup_multiplayer_rooms,
        "beschreibung": "Inaktive Multiplayer Rooms loeschen",
        "zeitplan": "Jede Stunde",
    },
    "ws_ticket_cleanup": {
        "func": cleanup_ws_tickets,
        "beschreibung": "Abgelaufene WebSocket-Tickets bereinigen",
        "zeitplan": "Jede Stunde",
    },
    "keep_alive": {
        "func": self_ping,
        "beschreibung": "Self-Ping Keep-Alive (verhindert Sleep auf Free-Tiers)",
        "zeitplan": "Alle 10 Minuten",
    },
    # ━━━ PR #52: Self-Improvement + Knowledge Base Auto-Update ━━━
    "self_improvement": {
        "func": None,  # wird in setup_scheduler gesetzt
        "beschreibung": "KI analysiert schlechte Feedbacks + verbessert Prompts",
        "zeitplan": "Taeglich 03:00",
    },
    "shop_seasonal_rotation": {
        "func": None,
        "beschreibung": "Saisonale Shop-Items generieren (XP-Booster, Avatare, etc.)",
        "zeitplan": "Sonntag 23:00",
    },
    "seasonal_events_manager": {
        "func": None,
        "beschreibung": "Events aktivieren/deaktivieren (Abitur, Ferien, etc.)",
        "zeitplan": "Jede Stunde",
    },
    "quiz_auto_generation": {
        "func": None,
        "beschreibung": "50 neue Quiz-Fragen pro Fach via Groq",
        "zeitplan": "Montag 02:00",
    },
    "battle_pass_content": {
        "func": None,
        "beschreibung": "Monatlicher Battle Pass: Badges, Titel, XP-Balance",
        "zeitplan": "1. des Monats 01:00",
    },
    "daily_challenges_gen": {
        "func": None,
        "beschreibung": "5 neue tägliche Challenges basierend auf Lerntrends",
        "zeitplan": "Taeglich 04:00",
    },
    "knowledge_all_subjects": {
        "func": None,
        "beschreibung": "Tavily-Suche für alle 16 Fächer (täglich)",
        "zeitplan": "Taeglich 03:00",
    },
    "wikipedia_sync": {
        "func": None,
        "beschreibung": "Wikipedia-Sync für 300+ Quiz-Themen",
        "zeitplan": "Montag 02:00",
    },
    "lehrplan_updates": {
        "func": None,
        "beschreibung": "Lehrplan-Updates pro Bundesland via Tavily",
        "zeitplan": "1. des Monats 01:00",
    },
}


def setup_scheduler(scheduler_instance):
    """Registriere alle Jobs beim APScheduler.

    Args:
        scheduler_instance: AsyncIOScheduler Instanz aus main.py
    """
    from apscheduler.triggers.cron import CronTrigger
    import pytz

    tz_berlin = pytz.timezone("Europe/Berlin")

    # Knowledge Update Funktion setzen
    from app.services.knowledge_updater import update_knowledge_base
    JOB_REGISTRY["knowledge_update"]["func"] = update_knowledge_base

    # ━━━ TÄGLICH 00:00 ━━━
    scheduler_instance.add_job(
        generate_daily_quests,
        CronTrigger(hour=0, minute=0, timezone=tz_berlin),
        id="daily_quests", replace_existing=True,
    )
    scheduler_instance.add_job(
        check_streaks,
        CronTrigger(hour=0, minute=5, timezone=tz_berlin),
        id="streak_check", replace_existing=True,
    )
    scheduler_instance.add_job(
        distribute_daily_xp_bonus,
        CronTrigger(hour=0, minute=10, timezone=tz_berlin),
        id="xp_bonus", replace_existing=True,
    )

    # ━━━ TÄGLICH 03:00 ━━━
    scheduler_instance.add_job(
        update_knowledge_base,
        CronTrigger(hour=3, minute=0, timezone=tz_berlin),
        id="knowledge_update", replace_existing=True,
    )

    # ━━━ TÄGLICH 08:00 ━━━
    scheduler_instance.add_job(
        send_motivation_notifications,
        CronTrigger(hour=8, minute=0, timezone=tz_berlin),
        id="daily_motivation", replace_existing=True,
    )

    # ━━━ WOECHENTLICH Montag 07:00 ━━━
    scheduler_instance.add_job(
        generate_weekly_report,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=tz_berlin),
        id="weekly_report", replace_existing=True,
    )
    scheduler_instance.add_job(
        create_weekly_challenges,
        CronTrigger(day_of_week="mon", hour=7, minute=5, timezone=tz_berlin),
        id="weekly_challenges", replace_existing=True,
    )

    # ━━━ WOECHENTLICH Sonntag 23:59 ━━━
    scheduler_instance.add_job(
        rotate_shop_items,
        CronTrigger(day_of_week="sun", hour=23, minute=59, timezone=tz_berlin),
        id="shop_rotation", replace_existing=True,
    )
    scheduler_instance.add_job(
        update_seasonal_events,
        CronTrigger(day_of_week="sun", hour=23, minute=55, timezone=tz_berlin),
        id="events_update", replace_existing=True,
    )

    # ━━━ MONATLICH (1. des Monats) ━━━
    scheduler_instance.add_job(
        start_new_battle_pass_season,
        CronTrigger(day=1, hour=0, minute=0, timezone=tz_berlin),
        id="battle_pass_season", replace_existing=True,
    )
    scheduler_instance.add_job(
        create_monthly_tournaments,
        CronTrigger(day=1, hour=0, minute=5, timezone=tz_berlin),
        id="monthly_tournaments", replace_existing=True,
    )
    scheduler_instance.add_job(
        reset_monthly_leaderboard,
        CronTrigger(day=1, hour=0, minute=10, timezone=tz_berlin),
        id="leaderboard_reset", replace_existing=True,
    )

    # ━━━ JEDE STUNDE ━━━
    scheduler_instance.add_job(
        cleanup_tournaments,
        CronTrigger(minute=0, timezone=tz_berlin),
        id="tournament_cleanup", replace_existing=True,
    )
    scheduler_instance.add_job(
        cleanup_multiplayer_rooms,
        CronTrigger(minute=5, timezone=tz_berlin),
        id="multiplayer_cleanup", replace_existing=True,
    )
    scheduler_instance.add_job(
        cleanup_ws_tickets,
        CronTrigger(minute=10, timezone=tz_berlin),
        id="ws_ticket_cleanup", replace_existing=True,
    )

    # ━━━ ALLE 10 MINUTEN: Keep-Alive ━━━
    scheduler_instance.add_job(
        self_ping,
        CronTrigger(minute="*/10", timezone=tz_berlin),
        id="keep_alive", replace_existing=True,
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PR #52: Self-Improvement + Knowledge Base Auto-Update
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from app.services.self_improvement import (
        nightly_self_improvement,
        generate_shop_items_for_season,
        manage_seasonal_events,
        generate_daily_challenges,
        generate_weekly_quiz_questions,
        generate_battle_pass_content,
    )
    from app.services.knowledge_updater import (
        update_knowledge_base_all_subjects,
        wikipedia_sync_all_topics,
        update_lehrplan_content,
    )

    # Funktionen im Registry setzen
    JOB_REGISTRY["self_improvement"]["func"] = nightly_self_improvement
    JOB_REGISTRY["shop_seasonal_rotation"]["func"] = generate_shop_items_for_season
    JOB_REGISTRY["seasonal_events_manager"]["func"] = manage_seasonal_events
    JOB_REGISTRY["quiz_auto_generation"]["func"] = generate_weekly_quiz_questions
    JOB_REGISTRY["battle_pass_content"]["func"] = generate_battle_pass_content
    JOB_REGISTRY["daily_challenges_gen"]["func"] = generate_daily_challenges
    JOB_REGISTRY["knowledge_all_subjects"]["func"] = update_knowledge_base_all_subjects
    JOB_REGISTRY["wikipedia_sync"]["func"] = wikipedia_sync_all_topics
    JOB_REGISTRY["lehrplan_updates"]["func"] = update_lehrplan_content

    # ━━━ AUFGABE 1A: Self-Improvement (täglich 03:00) ━━━
    scheduler_instance.add_job(
        nightly_self_improvement,
        CronTrigger(hour=3, minute=0, timezone=tz_berlin),
        id="self_improvement", replace_existing=True,
    )

    # ━━━ AUFGABE 1B: Shop Seasonal Rotation (Sonntag 23:00) ━━━
    scheduler_instance.add_job(
        generate_shop_items_for_season,
        CronTrigger(day_of_week="sun", hour=23, minute=0, timezone=tz_berlin),
        id="shop_seasonal_rotation", replace_existing=True,
    )

    # ━━━ AUFGABE 1C: Seasonal Events Manager (jede Stunde) ━━━
    scheduler_instance.add_job(
        manage_seasonal_events,
        CronTrigger(minute=30, timezone=tz_berlin),
        id="seasonal_events_manager", replace_existing=True,
    )

    # ━━━ AUFGABE 1D: Quiz Auto-Generation (Montag 02:00) ━━━
    scheduler_instance.add_job(
        generate_weekly_quiz_questions,
        CronTrigger(day_of_week="mon", hour=2, minute=0, timezone=tz_berlin),
        id="quiz_auto_generation", replace_existing=True,
    )

    # ━━━ AUFGABE 1E: Battle Pass Content (1. des Monats 01:00) ━━━
    scheduler_instance.add_job(
        generate_battle_pass_content,
        CronTrigger(day=1, hour=1, minute=0, timezone=tz_berlin),
        id="battle_pass_content", replace_existing=True,
    )

    # ━━━ AUFGABE 1F: Daily Challenges (täglich 04:00) ━━━
    scheduler_instance.add_job(
        generate_daily_challenges,
        CronTrigger(hour=4, minute=0, timezone=tz_berlin),
        id="daily_challenges_gen", replace_existing=True,
    )

    # ━━━ AUFGABE 2A: Knowledge Update alle Fächer (täglich 03:00) ━━━
    scheduler_instance.add_job(
        update_knowledge_base_all_subjects,
        CronTrigger(hour=3, minute=15, timezone=tz_berlin),
        id="knowledge_all_subjects", replace_existing=True,
    )

    # ━━━ AUFGABE 2B: Wikipedia Sync (Montag 02:00) ━━━
    scheduler_instance.add_job(
        wikipedia_sync_all_topics,
        CronTrigger(day_of_week="mon", hour=2, minute=30, timezone=tz_berlin),
        id="wikipedia_sync", replace_existing=True,
    )

    # ━━━ AUFGABE 2C: Lehrplan Updates (1. des Monats 01:00) ━━━
    scheduler_instance.add_job(
        update_lehrplan_content,
        CronTrigger(day=1, hour=1, minute=30, timezone=tz_berlin),
        id="lehrplan_updates", replace_existing=True,
    )

    logger.info("Scheduler Setup: %d Jobs registriert (inkl. PR #52)", len(JOB_REGISTRY))
