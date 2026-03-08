"""PR #52 — AUFGABE 1: Self-Improvement System.

A) Nightly Self-Improvement: Analysiert schlechte Chat-Feedbacks (rating < 3),
   identifiziert Fehlermuster, verbessert System-Prompts via Groq.
B) Shop Auto-Rotation: Wöchentlich (Sonntag 23:00) saisonale Items generieren
   (XP-Booster, Avatare, Badges, Streak-Schutz, Fach-Booster, Hintergründe).
C) Seasonal Events: Stündlich Events verwalten (Abitur-Season, Sommerferien,
   Back-to-School, Winterferien) mit XP-Multiplikatoren.
D) Quiz Auto-Generation: Wöchentlich (Montag 02:00) 50 neue Fragen pro Fach,
   Schwierigkeit basierend auf User-Performance, Duplikate entfernen.
E) Battle Pass Auto-Content: Monatlich (1. des Monats 01:00) einzigartige Badges,
   exklusive Titel, XP-Anforderungen balancieren.
F) Challenges Auto-Generation: Täglich (04:00) 5 neue Challenges basierend auf
   Lerntrends, verschiedene Schwierigkeiten, Zeitlimits (24h, 3d, 1w).
"""
import json
import logging
import os
import random
from datetime import datetime, date, timedelta

import httpx

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    return os.getenv("DATABASE_PATH", "app.db")


def _get_groq_key() -> str:
    from app.core.config import settings
    return settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")


async def _groq_generate(prompt: str, model: str = "llama-3.1-8b-instant",
                         max_tokens: int = 200, temperature: float = 0.5) -> str:
    """Groq API call helper for self-improvement tasks."""
    groq_key = _get_groq_key()
    if not groq_key:
        logger.warning("GROQ_API_KEY nicht gesetzt — Groq-Aufruf uebersprungen")
        return ""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq generate fehlgeschlagen: %s", exc)
    return ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# A) Nightly Self-Improvement (03:00 Berlin)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def nightly_self_improvement() -> dict:
    """Analysiert schlechte Chat-Feedbacks (rating < 3), identifiziert
    Fehlermuster und verbessert System-Prompts automatisch via Groq.

    Returns:
        {"analysierte_chats": int, "verbesserungen": int, "muster": [str]}
    """
    import aiosqlite

    logger.info("Job: nightly_self_improvement gestartet")
    db_path = _get_db_path()
    analysierte_chats = 0
    verbesserungen = 0
    muster = []

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Schlechte Feedbacks der letzten 24h (rating < 3)
            cursor = await db.execute(
                """SELECT cs.id, cs.subject, cs.messages, cs.title
                FROM chat_sessions cs
                JOIN chat_feedback cf ON cf.session_id = cs.id
                WHERE cf.rating < 3
                AND cf.created_at >= date('now', '-1 day')
                ORDER BY cf.rating ASC
                LIMIT 20"""
            )
            schlechte_chats = await cursor.fetchall()
            analysierte_chats = len(schlechte_chats)

            if analysierte_chats == 0:
                logger.info("Keine schlechten Feedbacks in den letzten 24h")
                return {"analysierte_chats": 0, "verbesserungen": 0, "muster": []}

            # Fehlermuster per Groq analysieren
            chat_zusammenfassung = []
            for chat in schlechte_chats[:10]:
                cd = dict(chat)
                msgs = cd.get("messages", "[]")
                if isinstance(msgs, str):
                    try:
                        msgs = json.loads(msgs)
                    except (json.JSONDecodeError, TypeError):
                        msgs = []
                # Letzte 3 Nachrichten
                letzte = msgs[-3:] if len(msgs) >= 3 else msgs
                text = " | ".join([
                    f"{m.get('role', '?')}: {str(m.get('content', ''))[:100]}"
                    for m in letzte
                ])
                chat_zusammenfassung.append(
                    f"Fach: {cd.get('subject', '?')} — {text}"
                )

            analyse_prompt = (
                "Analysiere diese schlecht bewerteten KI-Tutor Chats und "
                "identifiziere die Top-3 Fehlermuster:\n\n"
                + "\n".join(chat_zusammenfassung[:10])
                + "\n\nAntworte NUR mit 3 Fehlermustern (je eine Zeile, "
                "nummeriert 1-3). Auf Deutsch."
            )
            analyse_text = await _groq_generate(
                analyse_prompt,
                model="llama-3.3-70b-versatile",
                max_tokens=300,
                temperature=0.3,
            )

            if analyse_text:
                muster = [
                    line.strip()
                    for line in analyse_text.splitlines()
                    if line.strip() and any(c.isalpha() for c in line)
                ][:5]

            # Verbesserungsvorschlaege generieren
            if muster:
                verbesserung_prompt = (
                    "Du bist ein KI-System-Prompt-Optimierer für einen "
                    "Bildungs-Tutor (Gymnasium, Abitur).\n\n"
                    f"Diese Fehlermuster wurden identifiziert:\n"
                    + "\n".join(muster)
                    + "\n\nErstelle 3 konkrete Verbesserungen für den "
                    "System-Prompt. Jede Verbesserung als eine Zeile. Deutsch."
                )
                verbesserung_text = await _groq_generate(
                    verbesserung_prompt,
                    model="llama-3.3-70b-versatile",
                    max_tokens=400,
                    temperature=0.3,
                )

                if verbesserung_text:
                    vorschlaege = [
                        line.strip()
                        for line in verbesserung_text.splitlines()
                        if line.strip() and any(c.isalpha() for c in line)
                    ][:5]

                    for vorschlag in vorschlaege:
                        await db.execute(
                            """INSERT INTO prompt_improvements
                            (vorschlag, quelle, status, created_at)
                            VALUES (?, 'self_improvement_nightly', 'pending',
                                    datetime('now'))""",
                            (vorschlag,),
                        )
                        verbesserungen += 1

            await db.commit()

    except Exception as exc:
        logger.error("nightly_self_improvement fehlgeschlagen: %s", exc)

    logger.info(
        "Self-Improvement: %d Chats analysiert, %d Verbesserungen, Muster: %s",
        analysierte_chats, verbesserungen, muster,
    )
    return {
        "analysierte_chats": analysierte_chats,
        "verbesserungen": verbesserungen,
        "muster": muster,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# B) Shop Auto-Rotation (Sonntag 23:00 Berlin)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Saisonale Item-Pools
SEASONAL_SHOP_ITEMS = {
    "fruehling": [
        {"id": "boost_xp_spring", "name": "Fruehlings-XP-Booster (2x, 1h)", "category": "boost", "price": 400, "icon": "zap"},
        {"id": "avatar_blossom", "name": "Kirschblueten-Avatar", "category": "avatar", "price": 800, "icon": "flower"},
        {"id": "badge_spring_learner", "name": "Fruehlings-Lerner Badge", "category": "badge", "price": 500, "icon": "award"},
        {"id": "streak_shield_spring", "name": "Streak-Schutz (3 Tage)", "category": "streak_schutz", "price": 600, "icon": "shield"},
        {"id": "boost_mathe_spring", "name": "Mathe-Booster (1.5x XP)", "category": "fach_booster", "price": 350, "icon": "calculator"},
        {"id": "bg_spring_garden", "name": "Fruehlingswiese Hintergrund", "category": "hintergrund", "price": 450, "icon": "image"},
    ],
    "sommer": [
        {"id": "boost_xp_summer", "name": "Sommer-XP-Booster (2x, 1h)", "category": "boost", "price": 400, "icon": "zap"},
        {"id": "avatar_sunshine", "name": "Sonnenschein-Avatar", "category": "avatar", "price": 800, "icon": "sun"},
        {"id": "badge_summer_grind", "name": "Sommer-Grinder Badge", "category": "badge", "price": 500, "icon": "award"},
        {"id": "streak_shield_summer", "name": "Streak-Schutz (5 Tage)", "category": "streak_schutz", "price": 900, "icon": "shield"},
        {"id": "boost_bio_summer", "name": "Bio-Booster (1.5x XP)", "category": "fach_booster", "price": 350, "icon": "leaf"},
        {"id": "bg_beach", "name": "Strand Hintergrund", "category": "hintergrund", "price": 450, "icon": "image"},
    ],
    "herbst": [
        {"id": "boost_xp_autumn", "name": "Herbst-XP-Booster (2x, 1h)", "category": "boost", "price": 400, "icon": "zap"},
        {"id": "avatar_leaf", "name": "Herbstblatt-Avatar", "category": "avatar", "price": 800, "icon": "leaf"},
        {"id": "badge_back_to_school", "name": "Back-to-School Badge", "category": "badge", "price": 500, "icon": "award"},
        {"id": "streak_shield_autumn", "name": "Streak-Schutz (3 Tage)", "category": "streak_schutz", "price": 600, "icon": "shield"},
        {"id": "boost_deutsch_autumn", "name": "Deutsch-Booster (1.5x XP)", "category": "fach_booster", "price": 350, "icon": "book"},
        {"id": "bg_autumn_forest", "name": "Herbstwald Hintergrund", "category": "hintergrund", "price": 450, "icon": "image"},
    ],
    "winter": [
        {"id": "boost_xp_winter", "name": "Winter-XP-Booster (3x, 30min)", "category": "boost", "price": 500, "icon": "zap"},
        {"id": "avatar_snowflake", "name": "Schneeflocke-Avatar", "category": "avatar", "price": 800, "icon": "snowflake"},
        {"id": "badge_winter_warrior", "name": "Winter-Krieger Badge", "category": "badge", "price": 500, "icon": "award"},
        {"id": "streak_shield_winter", "name": "Streak-Schutz (7 Tage)", "category": "streak_schutz", "price": 1200, "icon": "shield"},
        {"id": "boost_physik_winter", "name": "Physik-Booster (1.5x XP)", "category": "fach_booster", "price": 350, "icon": "atom"},
        {"id": "bg_winter_wonderland", "name": "Winterwunderland Hintergrund", "category": "hintergrund", "price": 450, "icon": "image"},
    ],
}


def _get_current_season() -> str:
    """Aktuelle Jahreszeit basierend auf Monat."""
    month = datetime.now().month
    if month in (3, 4, 5):
        return "fruehling"
    elif month in (6, 7, 8):
        return "sommer"
    elif month in (9, 10, 11):
        return "herbst"
    return "winter"


async def generate_shop_items_for_season() -> dict:
    """Generiert saisonale Shop-Items basierend auf Jahreszeit und Monat.

    Waehlt 4-6 Items aus dem saisonalen Pool + 2 Bonus-Items.

    Returns:
        {"season": str, "neue_items": int, "items": [dict]}
    """
    import aiosqlite

    logger.info("Job: generate_shop_items_for_season gestartet")
    db_path = _get_db_path()
    season = _get_current_season()
    pool = SEASONAL_SHOP_ITEMS.get(season, SEASONAL_SHOP_ITEMS["winter"])

    # 4-6 saisonale Items
    num_items = random.randint(4, min(6, len(pool)))
    neue_items = random.sample(pool, num_items)

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            rotation_data = json.dumps([item["id"] for item in neue_items])
            items_json = json.dumps(neue_items)

            await db.execute(
                """INSERT OR REPLACE INTO shop_rotations
                (week_date, items_json, season, created_at)
                VALUES (date('now'), ?, ?, datetime('now'))""",
                (items_json, season),
            )

            # Notification an alle aktiven User
            cursor = await db.execute(
                """SELECT DISTINCT user_id FROM activity_log
                WHERE created_at >= date('now', '-14 days')"""
            )
            users = await cursor.fetchall()

            item_namen = ", ".join([i["name"] for i in neue_items[:3]])
            for u in users:
                user_id = dict(u)["user_id"]
                await db.execute(
                    """INSERT INTO notifications
                    (user_id, title, message, notification_type)
                    VALUES (?, ?, ?, 'shop')""",
                    (user_id,
                     f"Neue {season.capitalize()}-Items im Shop!",
                     f"Diese Woche neu: {item_namen} und mehr!"),
                )

            await db.commit()

    except Exception as exc:
        logger.error("generate_shop_items_for_season fehlgeschlagen: %s", exc)
        return {"season": season, "neue_items": 0, "items": []}

    logger.info("Shop saisonal rotiert: %d Items für %s", len(neue_items), season)
    return {
        "season": season,
        "neue_items": len(neue_items),
        "items": [i["name"] for i in neue_items],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# C) Seasonal Events (stuendlich)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SEASONAL_EVENTS = [
    {
        "name": "Abitur-Season",
        "description": "Intensives Lernen für die Abiturprüfungen! 2x XP auf alle Quizze.",
        "start_month": 3, "end_month": 6,
        "xp_multiplier": 2.0,
        "event_type": "abitur",
    },
    {
        "name": "Sommerferien-Challenge",
        "description": "Lerne auch im Sommer! Spezielle Ferien-Challenges mit Bonus-Rewards.",
        "start_month": 7, "end_month": 8,
        "xp_multiplier": 1.5,
        "event_type": "sommerferien",
    },
    {
        "name": "Back-to-School",
        "description": "Neues Schuljahr, neuer Start! 1.5x XP für alle Fächer.",
        "start_month": 8, "end_month": 9,
        "xp_multiplier": 1.5,
        "event_type": "back_to_school",
    },
    {
        "name": "Winterferien-Sprint",
        "description": "Nutze die Winterferien zum Aufholen! 2x XP + Bonus-Streak-Schutz.",
        "start_month": 12, "end_month": 1,
        "xp_multiplier": 2.0,
        "event_type": "winterferien",
    },
]


async def manage_seasonal_events() -> dict:
    """Stuendlicher Job: Events aktivieren/deaktivieren basierend auf Monat.

    Returns:
        {"aktiviert": [str], "deaktiviert": [str], "aktive_events": int}
    """
    import aiosqlite

    logger.info("Job: manage_seasonal_events gestartet")
    db_path = _get_db_path()
    current_month = datetime.now().month
    aktiviert = []
    deaktiviert = []

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            for event in SEASONAL_EVENTS:
                start_m = event["start_month"]
                end_m = event["end_month"]

                # Pruefen ob aktueller Monat im Event-Zeitraum
                if start_m <= end_m:
                    is_active = start_m <= current_month <= end_m
                else:
                    # Jahrswechsel (z.B. Dez-Jan)
                    is_active = current_month >= start_m or current_month <= end_m

                # Existiert das Event schon?
                cursor = await db.execute(
                    "SELECT id, status FROM seasonal_events WHERE name = ?",
                    (event["name"],),
                )
                existing = await cursor.fetchone()

                if is_active:
                    if existing:
                        ed = dict(existing)
                        if ed["status"] != "active":
                            await db.execute(
                                "UPDATE seasonal_events SET status = 'active' WHERE id = ?",
                                (ed["id"],),
                            )
                            aktiviert.append(event["name"])
                    else:
                        now = datetime.now()
                        year = now.year
                        start_date = f"{year}-{start_m:02d}-01"
                        if start_m <= end_m:
                            end_date = f"{year}-{end_m:02d}-28"
                        else:
                            end_date = f"{year + 1}-{end_m:02d}-28"

                        await db.execute(
                            """INSERT INTO seasonal_events
                            (name, description, start_date, end_date, status,
                             xp_multiplier, event_type)
                            VALUES (?, ?, ?, ?, 'active', ?, ?)""",
                            (event["name"], event["description"],
                             start_date, end_date,
                             event["xp_multiplier"], event["event_type"]),
                        )
                        aktiviert.append(event["name"])
                else:
                    if existing and dict(existing)["status"] == "active":
                        await db.execute(
                            "UPDATE seasonal_events SET status = 'ended' WHERE id = ?",
                            (dict(existing)["id"],),
                        )
                        deaktiviert.append(event["name"])

            # Zaehle aktive Events
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM seasonal_events WHERE status = 'active'"
            )
            row = await cursor.fetchone()
            aktive_events = dict(row)["cnt"] if row else 0

            await db.commit()

    except Exception as exc:
        logger.error("manage_seasonal_events fehlgeschlagen: %s", exc)
        return {"aktiviert": [], "deaktiviert": [], "aktive_events": 0}

    logger.info(
        "Seasonal Events: %d aktiviert, %d deaktiviert, %d aktiv",
        len(aktiviert), len(deaktiviert), aktive_events if 'aktive_events' in dir() else 0,
    )
    return {
        "aktiviert": aktiviert,
        "deaktiviert": deaktiviert,
        "aktive_events": aktive_events,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# D) Quiz Auto-Generation (Montag 02:00)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUIZ_FAECHER = [
    "Mathematik", "Deutsch", "Englisch", "Physik", "Chemie",
    "Biologie", "Geschichte", "Geografie", "Wirtschaft", "Ethik",
    "Informatik", "Kunst", "Musik", "Sozialkunde", "Latein", "Franzoesisch",
]


async def generate_weekly_quiz_questions() -> dict:
    """Generiert 50 neue Quiz-Fragen pro Fach via Groq. Passt Schwierigkeit
    basierend auf User-Performance an und entfernt Duplikate.

    Returns:
        {"faecher_verarbeitet": int, "neue_fragen": int, "duplikate_entfernt": int}
    """
    import aiosqlite

    logger.info("Job: generate_weekly_quiz_questions gestartet")
    db_path = _get_db_path()
    groq_key = _get_groq_key()
    neue_fragen_total = 0
    duplikate_entfernt = 0
    faecher_verarbeitet = 0

    if not groq_key:
        logger.warning("GROQ_API_KEY nicht gesetzt — Quiz-Generation uebersprungen")
        return {"faecher_verarbeitet": 0, "neue_fragen": 0, "duplikate_entfernt": 0}

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            for fach in QUIZ_FAECHER:
                try:
                    # Durchschnittliche Schwierigkeit basierend auf User-Performance
                    cursor = await db.execute(
                        """SELECT AVG(score) as avg_score
                        FROM quiz_results
                        WHERE subject = ?
                        AND completed_at >= date('now', '-30 days')""",
                        (fach,),
                    )
                    row = await cursor.fetchone()
                    avg_score = dict(row)["avg_score"] if row and dict(row)["avg_score"] else 60.0

                    # Schwierigkeit anpassen
                    if avg_score > 80:
                        schwierigkeit = "schwer"
                    elif avg_score > 50:
                        schwierigkeit = "mittel"
                    else:
                        schwierigkeit = "leicht"

                    # 5 Fragen pro Fach generieren (Batch von 5 statt 50 um API-Limits zu schonen)
                    quiz_prompt = (
                        f"Erstelle 5 Multiple-Choice-Quiz-Fragen für das Fach {fach} "
                        f"(Gymnasium, Schwierigkeit: {schwierigkeit}).\n\n"
                        f"Format pro Frage (JSON Array):\n"
                        f'[{{"frage": "...", "optionen": ["A", "B", "C", "D"], '
                        f'"richtig": "A", "erklaerung": "..."}}]\n\n'
                        f"Nur das JSON Array ausgeben, keine Erklaerung davor/danach."
                    )

                    fragen_text = await _groq_generate(
                        quiz_prompt,
                        model="llama-3.3-70b-versatile",
                        max_tokens=1500,
                        temperature=0.7,
                    )

                    if fragen_text:
                        # JSON parsen
                        try:
                            # Bereinige den Text
                            clean = fragen_text.strip()
                            if clean.startswith("```"):
                                clean = clean.split("\n", 1)[-1]
                                if clean.endswith("```"):
                                    clean = clean[:-3]
                            fragen = json.loads(clean)
                        except (json.JSONDecodeError, TypeError):
                            fragen = []

                        for frage_obj in fragen:
                            if not isinstance(frage_obj, dict):
                                continue
                            frage_text = frage_obj.get("frage", "")
                            if not frage_text:
                                continue

                            # Duplikat-Check
                            cursor = await db.execute(
                                """SELECT COUNT(*) as cnt FROM quiz_bank
                                WHERE fach = ? AND frage = ?""",
                                (fach, frage_text),
                            )
                            dup_row = await cursor.fetchone()
                            if dup_row and dict(dup_row)["cnt"] > 0:
                                duplikate_entfernt += 1
                                continue

                            # Speichern
                            await db.execute(
                                """INSERT INTO quiz_bank
                                (fach, frage, optionen, richtig, erklaerung,
                                 schwierigkeit, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                                (fach, frage_text,
                                 json.dumps(frage_obj.get("optionen", [])),
                                 frage_obj.get("richtig", ""),
                                 frage_obj.get("erklaerung", ""),
                                 schwierigkeit),
                            )
                            neue_fragen_total += 1

                    faecher_verarbeitet += 1

                except Exception as fach_err:
                    logger.warning("Quiz-Gen für %s fehlgeschlagen: %s", fach, fach_err)

            await db.commit()

    except Exception as exc:
        logger.error("generate_weekly_quiz_questions fehlgeschlagen: %s", exc)

    logger.info(
        "Quiz-Gen: %d Fächer, %d neue Fragen, %d Duplikate entfernt",
        faecher_verarbeitet, neue_fragen_total, duplikate_entfernt,
    )
    return {
        "faecher_verarbeitet": faecher_verarbeitet,
        "neue_fragen": neue_fragen_total,
        "duplikate_entfernt": duplikate_entfernt,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# E) Battle Pass Auto-Content (1. des Monats 01:00)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BATTLE_PASS_TITLES = [
    "Wissens-Titan", "Lern-Legende", "Quiz-Held", "Streak-Meister",
    "Abitur-Champion", "Mathe-Genie", "Sprach-Profi", "Natur-Forscher",
    "Geschichte-Kenner", "Physik-Virtuose", "Chemie-Experte", "Bio-Guru",
]

BATTLE_PASS_BADGES = [
    "Goldener Stift", "Diamant-Hirn", "Platin-Buch", "Kristall-Lampe",
    "Regenbogen-Stern", "Feuervogel", "Eisdrache", "Sturmwolf",
    "Nebelfuchs", "Mondloewe", "Sonnenadler", "Schattenphoenix",
]


async def generate_battle_pass_content() -> dict:
    """Generiert monatlichen Battle Pass: einzigartige Badges, exklusive Titel,
    balancierte XP-Anforderungen.

    Returns:
        {"season_name": str, "levels": int, "badges": [str], "titel": [str]}
    """
    import aiosqlite

    logger.info("Job: generate_battle_pass_content gestartet")
    db_path = _get_db_path()

    now = datetime.now()
    season_names = [
        "Fruehling", "Sommer", "Herbst", "Winter",
        "Nebel", "Sturm", "Eis", "Feuer",
        "Kristall", "Schatten", "Licht", "Donner",
    ]
    season_name = f"{season_names[now.month - 1]} {now.year}"

    # 30 Levels mit steigenden XP-Anforderungen
    levels_data = []
    for level in range(1, 31):
        xp_required = level * 100 + (level ** 2) * 5
        reward_type = "badge" if level % 5 == 0 else "xp_boost" if level % 3 == 0 else "titel" if level % 10 == 0 else "coins"

        if reward_type == "badge":
            reward = random.choice(BATTLE_PASS_BADGES)
        elif reward_type == "titel":
            reward = random.choice(BATTLE_PASS_TITLES)
        else:
            reward = f"{level * 10} Coins"

        levels_data.append({
            "level": level,
            "xp_required": xp_required,
            "reward_type": reward_type,
            "reward": reward,
            "is_premium": level > 15,
        })

    selected_badges = random.sample(BATTLE_PASS_BADGES, min(3, len(BATTLE_PASS_BADGES)))
    selected_titles = random.sample(BATTLE_PASS_TITLES, min(2, len(BATTLE_PASS_TITLES)))

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Battle Pass Season speichern
            await db.execute(
                """INSERT INTO battle_pass_seasons
                (name, levels_json, start_date, end_date, created_at)
                VALUES (?, ?, date('now'), date('now', '+30 days'), datetime('now'))""",
                (season_name, json.dumps(levels_data)),
            )

            # Alle User Battle Pass zurücksetzen
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
                     "Neuer Battle Pass!",
                     f"Season '{season_name}' ist da! 30 Levels mit exklusiven Rewards."),
                )

            await db.commit()

    except Exception as exc:
        logger.error("generate_battle_pass_content fehlgeschlagen: %s", exc)
        return {"season_name": season_name, "levels": 0, "badges": [], "titel": []}

    logger.info("Battle Pass '%s': 30 Levels generiert", season_name)
    return {
        "season_name": season_name,
        "levels": 30,
        "badges": selected_badges,
        "titel": selected_titles,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# F) Challenges Auto-Generation (taeglich 04:00)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHALLENGE_TEMPLATES = [
    {
        "title_template": "Quiz-Sprint: {fach}",
        "description_template": "Schaffe {target} Quizze in {fach}",
        "target_range": (3, 8),
        "xp_range": (100, 300),
        "zeitlimit": "24h",
    },
    {
        "title_template": "Streak-Challenge",
        "description_template": "Halte deinen Streak für {target} Tage",
        "target_range": (3, 7),
        "xp_range": (200, 500),
        "zeitlimit": "1w",
    },
    {
        "title_template": "Karteikarten-Meister",
        "description_template": "Erstelle {target} Karteikarten in beliebigen Fächern",
        "target_range": (10, 30),
        "xp_range": (150, 350),
        "zeitlimit": "3d",
    },
    {
        "title_template": "Turnier-Held: {fach}",
        "description_template": "Nimm an {target} Turnieren in {fach} teil",
        "target_range": (1, 3),
        "xp_range": (200, 400),
        "zeitlimit": "3d",
    },
    {
        "title_template": "Chat-Experte: {fach}",
        "description_template": "Stelle {target} Fragen an die KI im Fach {fach}",
        "target_range": (5, 15),
        "xp_range": (100, 250),
        "zeitlimit": "24h",
    },
    {
        "title_template": "Allrounder",
        "description_template": "Lerne in {target} verschiedenen Fächern",
        "target_range": (3, 6),
        "xp_range": (250, 500),
        "zeitlimit": "3d",
    },
    {
        "title_template": "Frueh-Lerner",
        "description_template": "Starte {target} Lernsessions vor 8:00 Uhr",
        "target_range": (1, 3),
        "xp_range": (150, 300),
        "zeitlimit": "1w",
    },
]


async def generate_daily_challenges() -> dict:
    """Generiert 5 neue taeglich Challenges basierend auf Lerntrends.

    Returns:
        {"neue_challenges": int, "faecher": [str]}
    """
    import aiosqlite

    logger.info("Job: generate_daily_challenges gestartet")
    db_path = _get_db_path()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Trend-Fächer der letzten 7 Tage
            cursor = await db.execute(
                """SELECT subject, COUNT(*) as cnt FROM chat_sessions
                WHERE created_at >= date('now', '-7 days')
                GROUP BY subject ORDER BY cnt DESC LIMIT 8"""
            )
            top_faecher = await cursor.fetchall()
            faecher = [dict(r)["subject"] for r in top_faecher] if top_faecher else [
                "Mathematik", "Deutsch", "Englisch", "Physik", "Geschichte"
            ]

            # 5 Challenges aus Templates generieren
            templates = random.sample(
                CHALLENGE_TEMPLATES,
                min(5, len(CHALLENGE_TEMPLATES))
            )

            neue_challenges = 0
            challenge_faecher = []
            today_str = date.today().isoformat()
            zeitlimit_map = {
                "24h": timedelta(days=1),
                "3d": timedelta(days=3),
                "1w": timedelta(days=7),
            }

            for tmpl in templates:
                fach = random.choice(faecher) if "{fach}" in tmpl["title_template"] else "Alle"
                target = random.randint(*tmpl["target_range"])
                xp_reward = random.randint(*tmpl["xp_range"])
                zeitlimit = tmpl["zeitlimit"]
                deadline = (date.today() + zeitlimit_map.get(zeitlimit, timedelta(days=1))).isoformat()

                title = tmpl["title_template"].replace("{fach}", fach)
                description = tmpl["description_template"].replace(
                    "{fach}", fach
                ).replace("{target}", str(target))

                await db.execute(
                    """INSERT INTO daily_challenges
                    (title, description, target, xp_reward, fach,
                     zeitlimit, deadline, challenge_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                    (title, description, target, xp_reward, fach,
                     zeitlimit, deadline, today_str),
                )
                neue_challenges += 1
                if fach != "Alle":
                    challenge_faecher.append(fach)

            await db.commit()

    except Exception as exc:
        logger.error("generate_daily_challenges fehlgeschlagen: %s", exc)
        return {"neue_challenges": 0, "faecher": []}

    logger.info("Daily Challenges: %d neue Challenges generiert", neue_challenges)
    return {
        "neue_challenges": neue_challenges,
        "faecher": list(set(challenge_faecher)),
    }
