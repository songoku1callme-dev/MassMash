"""
Ghost Founder Engine — läuft nachts, schickt morgens.
Kein manueller Eingriff nötig.

Block 3: 3 automatische Jobs:
1. Tägliche personalisierte Lern-Impulse (08:00)
2. Inaktivitäts-Reaktivierung (18:00)
3. Wöchentlicher Lernbericht (Sonntag 20:00)
"""
import logging
import os
from datetime import datetime, timedelta

import aiosqlite

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
FROM = "Lumnos \u2726 <onboarding@resend.dev>"
APP_URL = os.getenv(
    "LUMNOS_APP_URL",
    "https://mass-mash-git-devin-1772462-fd938d-songoku1callme-devs-projects.vercel.app",
)


async def _groq_generate(prompt: str, max_tokens: int = 80, temperature: float = 0.9) -> str:
    """Generate text via Groq API (lightweight helper)."""
    if not GROQ_API_KEY:
        return ""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Groq generate failed: %s", exc)
    return ""


async def _send_email_resend(to: str, subject: str, html: str) -> bool:
    """Send email via Resend API."""
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("RESEND_API_KEY not set, skipping email to %s", to)
        return False
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"from": FROM, "to": [to], "subject": subject, "html": html},
            )
            if resp.status_code in (200, 201):
                logger.info("Ghost Founder email sent to %s: %s", to, subject)
                return True
            logger.warning("Resend error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.error("Ghost Founder email failed: %s", exc)
    return False


# ─────────────────────────────────────────────
# JOB 1: Tägliche personalisierte Lern-Impulse
# Läuft täglich um 08:00 Uhr
# ─────────────────────────────────────────────
async def send_daily_impulse():
    """Analyse schwächstes Fach und sende KI-generierten Impuls."""
    logger.info("Ghost Founder: Tägliche Impulse starten")
    db_path = os.getenv("DATABASE_PATH", "app.db")
    count = 0
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, username, email, streak_days FROM users "
                "WHERE email IS NOT NULL AND email != ''"
            )
            users = await cursor.fetchall()

            for u in users:
                ud = dict(u)
                try:
                    # Schwächstes Fach finden (letzte 7 Tage)
                    qc = await db.execute(
                        """SELECT subject, AVG(score) as avg_score
                        FROM quiz_results
                        WHERE user_id = ? AND created_at >= date('now', '-7 days')
                        GROUP BY subject
                        ORDER BY avg_score ASC LIMIT 1""",
                        (ud["id"],),
                    )
                    row = await qc.fetchone()
                    if row:
                        rd = dict(row)
                        schwächstes_fach = rd.get("subject", "Mathematik")
                        niedrigster_score = rd.get("avg_score", 0) or 0
                    else:
                        schwächstes_fach = "Mathematik"
                        niedrigster_score = 0

                    # KI generiert persönliche Nachricht
                    text = await _groq_generate(
                        f"Schreibe eine kurze, motivierende Lern-Erinnerung "
                        f"(2 Sätze, locker und freundlich) für:\n"
                        f"Name: {ud['username']}\n"
                        f"Schwächstes Fach diese Woche: {schwächstes_fach} "
                        f"({niedrigster_score:.0f}% richtig)\n"
                        f"Streak: {ud.get('streak_days', 0)} Tage\n"
                        f"Ton: Wie ein cooler Lernbuddy, kurz + motivierend.\n"
                        f"Nutze echte deutsche Umlaute (ä ö ü ß).",
                        max_tokens=80,
                        temperature=0.9,
                    )
                    if not text:
                        text = f"Hey {ud['username']}! Heute wäre ein guter Tag für {schwächstes_fach}. Los geht's!"

                    streak_html = ""
                    streak_val = ud.get("streak_days", 0) or 0
                    if streak_val > 2:
                        streak_html = (
                            '<div style="background:rgba(249,115,22,0.1);border:1px solid '
                            'rgba(249,115,22,0.25);border-radius:12px;padding:12px;'
                            f'margin-bottom:20px;"><div style="color:#fb923c;font-size:13px;'
                            f'font-weight:700;">\U0001f525 {streak_val} Tage Streak — nicht '
                            f"unterbrechen!</div></div>"
                        )

                    html = f"""<!DOCTYPE html><html><body style="background:#0a0f1e;color:#f1f5f9;
font-family:Inter,sans-serif;padding:32px 20px;margin:0;">
<div style="max-width:480px;margin:0 auto;">
  <div style="text-align:center;margin-bottom:24px;">
    <div style="font-size:40px;">\u2726</div>
    <h2 style="color:#fff;margin:8px 0;font-size:22px;">
      Guten Morgen, {ud['username']}!
    </h2>
  </div>
  <div style="background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.3);
              border-radius:16px;padding:20px;margin-bottom:20px;">
    <p style="color:#cbd5e1;margin:0;line-height:1.7;font-size:15px;">{text}</p>
  </div>
  <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.25);
              border-radius:12px;padding:16px;margin-bottom:20px;">
    <div style="color:#f87171;font-size:12px;font-weight:700;margin-bottom:6px;">
      \u26A0\uFE0F FOKUS HEUTE</div>
    <div style="color:#fff;font-weight:700;">{schwächstes_fach}</div>
    <div style="color:#94a3b8;font-size:13px;">
      {niedrigster_score:.0f}% letzte Woche — heute besser machen!</div>
  </div>
  {streak_html}
  <div style="text-align:center;">
    <a href="{APP_URL}/quiz?fach={schwächstes_fach}"
       style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);
              color:white;padding:12px 28px;border-radius:12px;
              text-decoration:none;font-weight:700;font-size:14px;">
      {schwächstes_fach} jetzt üben \u2192
    </a>
  </div>
  <p style="color:#475569;font-size:11px;text-align:center;margin-top:24px;">
    Lumnos \u00b7 Abmelden: Einstellungen \u2192 Benachrichtigungen
  </p>
</div></body></html>"""

                    await _send_email_resend(
                        ud["email"],
                        f"\u2726 Guten Morgen, {ud['username']}! Heute: {schwächstes_fach}",
                        html,
                    )
                    count += 1
                except Exception as exc:
                    logger.warning("Impulse-Fehler für %s: %s", ud.get("email"), exc)
                    continue
    except Exception as exc:
        logger.error("Ghost Founder daily impulse failed: %s", exc)

    logger.info("Ghost Founder: %d Impulse versendet", count)


# ─────────────────────────────────────────────
# JOB 2: Inaktivitäts-Reaktivierung (nach 2 Tagen)
# Läuft täglich um 18:00 Uhr
# ─────────────────────────────────────────────
async def check_inactive_users():
    """User die genau 2 Tage inaktiv sind re-engagen."""
    logger.info("Ghost Founder: Inaktivitäts-Check starten")
    db_path = os.getenv("DATABASE_PATH", "app.db")
    count = 0
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            # Users whose last_active is exactly 2 days ago
            cursor = await db.execute(
                """SELECT id, username, email, streak_days FROM users
                WHERE email IS NOT NULL AND email != ''
                AND DATE(last_active) = DATE('now', '-2 days')"""
            )
            inaktive = await cursor.fetchall()

            for u in inaktive:
                ud = dict(u)
                try:
                    text = await _groq_generate(
                        f"Schreibe eine kurze Re-Engagement Nachricht (2 Sätze) "
                        f"für {ud['username']}. "
                        f"Er/sie war 2 Tage nicht aktiv. Buddy-Ton, locker, "
                        f"nicht aufdringlich. "
                        f"Echte deutsche Umlaute (ä ö ü ß).",
                        max_tokens=60,
                        temperature=0.95,
                    )
                    if not text:
                        text = f"Hey {ud['username']}! Wir vermissen dich. Komm zurück und lerne weiter!"

                    html = f"""<!DOCTYPE html><html><body style="background:#0a0f1e;color:#f1f5f9;
font-family:Inter,sans-serif;padding:32px 20px;">
<div style="max-width:460px;margin:0 auto;text-align:center;">
  <div style="font-size:48px;margin-bottom:16px;">\U0001f919</div>
  <h2 style="color:#fff;font-size:20px;margin:0 0 16px;">
    Wir vermissen dich, {ud['username']}!
  </h2>
  <p style="color:#94a3b8;line-height:1.7;font-size:14px;margin-bottom:24px;">{text}</p>
  <a href="{APP_URL}/chat"
     style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);
            color:white;padding:12px 28px;border-radius:12px;
            text-decoration:none;font-weight:700;">
    Weiterlernen \u2192
  </a>
</div></body></html>"""

                    await _send_email_resend(
                        ud["email"],
                        f"Hey {ud['username']}, alles okay? \u2726",
                        html,
                    )
                    count += 1
                except Exception as exc:
                    logger.warning("Reactivation-Fehler %s: %s", ud.get("email"), exc)

    except Exception as exc:
        logger.error("Ghost Founder inactivity check failed: %s", exc)

    logger.info("Ghost Founder: %d Re-Engagement E-Mails", count)


# ─────────────────────────────────────────────
# JOB 3: Wöchentlicher Lernbericht (Sonntag 20:00)
# ─────────────────────────────────────────────
async def send_weekly_report():
    """Wöchentlicher Bericht mit Statistiken."""
    logger.info("Ghost Founder: Wochenberichte starten")
    db_path = os.getenv("DATABASE_PATH", "app.db")
    count = 0
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, username, email, streak_days FROM users "
                "WHERE email IS NOT NULL AND email != ''"
            )
            users = await cursor.fetchall()

            for u in users:
                ud = dict(u)
                try:
                    # Chats diese Woche
                    cc = await db.execute(
                        """SELECT COUNT(*) as cnt FROM chat_messages
                        WHERE user_id = ? AND role = 'user'
                        AND created_at >= date('now', '-7 days')""",
                        (ud["id"],),
                    )
                    cr = await cc.fetchone()
                    chats = dict(cr).get("cnt", 0) if cr else 0

                    # Quizze diese Woche
                    qc = await db.execute(
                        """SELECT COUNT(*) as cnt FROM quiz_results
                        WHERE user_id = ? AND created_at >= date('now', '-7 days')""",
                        (ud["id"],),
                    )
                    qr = await qc.fetchone()
                    quizze = dict(qr).get("cnt", 0) if qr else 0

                    if chats == 0 and quizze == 0:
                        continue  # Inaktive komplett überspringen

                    streak = ud.get("streak_days", 0) or 0
                    xp = 0  # Placeholder

                    html = f"""<!DOCTYPE html><html><body style="background:#0a0f1e;color:#f1f5f9;
font-family:Inter,sans-serif;padding:32px 20px;">
<div style="max-width:480px;margin:0 auto;">
  <div style="text-align:center;margin-bottom:24px;">
    <div style="font-size:36px;">\U0001f4ca</div>
    <h2 style="color:#fff;font-size:22px;margin:8px 0;">Deine Woche in Zahlen</h2>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px;">
    <div style="background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.3);
                border-radius:14px;padding:18px;text-align:center;">
      <div style="font-size:32px;font-weight:900;color:#fff;">{chats}</div>
      <div style="color:#94a3b8;font-size:12px;">KI-Chats</div>
    </div>
    <div style="background:rgba(6,182,212,0.12);border:1px solid rgba(6,182,212,0.3);
                border-radius:14px;padding:18px;text-align:center;">
      <div style="font-size:32px;font-weight:900;color:#fff;">{quizze}</div>
      <div style="color:#94a3b8;font-size:12px;">Quizze</div>
    </div>
    <div style="background:rgba(249,115,22,0.12);border:1px solid rgba(249,115,22,0.3);
                border-radius:14px;padding:18px;text-align:center;">
      <div style="font-size:32px;font-weight:900;color:#fff;">{streak}\U0001f525</div>
      <div style="color:#94a3b8;font-size:12px;">Tage Streak</div>
    </div>
    <div style="background:rgba(139,92,246,0.12);border:1px solid rgba(139,92,246,0.3);
                border-radius:14px;padding:18px;text-align:center;">
      <div style="font-size:32px;font-weight:900;color:#fff;">{xp}</div>
      <div style="color:#94a3b8;font-size:12px;">XP verdient</div>
    </div>
  </div>
  <div style="text-align:center;">
    <a href="{APP_URL}/dashboard"
       style="display:inline-block;background:linear-gradient(135deg,#6366f1,#8b5cf6);
              color:white;padding:12px 28px;border-radius:12px;
              text-decoration:none;font-weight:700;">
      Nächste Woche noch besser \u2192
    </a>
  </div>
</div></body></html>"""

                    await _send_email_resend(
                        ud["email"],
                        f"\U0001f4ca Dein Lumnos-Wochenbericht, {ud['username']}",
                        html,
                    )
                    count += 1
                except Exception as exc:
                    logger.warning("Report-Fehler %s: %s", ud.get("email"), exc)

    except Exception as exc:
        logger.error("Ghost Founder weekly report failed: %s", exc)

    logger.info("Ghost Founder: %d Wochenberichte versendet", count)


# ─────────────────────────────────────────────
# JOB 4: Nightly Knowledge Crawl (03:00)
# LUMNOS Self-Evolution Block 6
# ─────────────────────────────────────────────
async def nightly_crawl():
    """Nächtlicher Crawl der Bildungsquellen für FAISS-Index."""
    logger.info("Evolution: Nightly Knowledge Crawl starten")
    try:
        from app.services.deep_crawler import nightly_knowledge_update
        await nightly_knowledge_update()
        logger.info("Evolution: Nightly Crawl abgeschlossen")
    except Exception as exc:
        logger.error("Evolution: Nightly Crawl fehlgeschlagen: %s", exc)


# ─────────────────────────────────────────────
# JOB 5: Wöchentliche Prompt-Optimierung (Montag 04:00)
# LUMNOS Self-Evolution Block 6
# ─────────────────────────────────────────────
async def weekly_prompt_optimization():
    """Wöchentliche Analyse negativer Feedbacks und Prompt-Verbesserung."""
    logger.info("Evolution: Wöchentliche Prompt-Optimierung starten")
    try:
        from app.services.prompt_optimizer import analyze_feedback_and_optimize
        await analyze_feedback_and_optimize()
        logger.info("Evolution: Prompt-Optimierung abgeschlossen")
    except Exception as exc:
        logger.error("Evolution: Prompt-Optimierung fehlgeschlagen: %s", exc)
