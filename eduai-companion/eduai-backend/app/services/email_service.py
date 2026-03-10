"""Email service using Resend API.

Supreme 12.0 Phase 4: 6 email templates with HTML styling.
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = "Lumnos <onboarding@resend.dev>"


async def _send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend API. Returns True on success."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set, skipping email to %s", to)
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html},
            )
            if resp.status_code in (200, 201):
                logger.info("Email sent to %s: %s", to, subject)
                return True
            logger.warning("Resend error %s: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("Email send failed: %s", e)
    return False


def _base_template(content: str) -> str:
    """Wrap content in a styled email base template."""
    return f"""
    <div style="font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 600px; margin: 0 auto;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 3px; border-radius: 16px;">
      <div style="background: #ffffff; border-radius: 14px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #4f46e5, #7c3aed); padding: 24px 32px; text-align: center;">
          <h1 style="color: white; margin: 0; font-size: 24px;">Lumnos Companion</h1>
          <p style="color: rgba(255,255,255,0.8); margin: 4px 0 0; font-size: 14px;">Dein persönlicher KI-Tutor</p>
        </div>
        <div style="padding: 32px;">
          {content}
        </div>
        <div style="background: #f9fafb; padding: 16px 32px; text-align: center; border-top: 1px solid #e5e7eb;">
          <p style="color: #9ca3af; font-size: 12px; margin: 0;">
            Lumnos Companion | DSGVO-konform | <a href="#" style="color: #6366f1;">Abmelden</a>
          </p>
        </div>
      </div>
    </div>
    """


async def send_welcome_email(to: str, username: str) -> bool:
    """Template 1: Welcome email after registration."""
    content = f"""
    <h2 style="color: #1f2937;">Willkommen bei Lumnos, {username}!</h2>
    <p style="color: #4b5563; line-height: 1.6;">
      Schön, dass du dabei bist! Mit Lumnos hast du jetzt Zugang zu:
    </p>
    <ul style="color: #4b5563; line-height: 2;">
      <li>20 KI-Persönlichkeiten die dir alles erklären</li>
      <li>Tägliche Turniere gegen andere Schüler</li>
      <li>IQ-Test mit wissenschaftlichen Fragen</li>
      <li>Abitur-Simulation für alle 16 Fächer</li>
    </ul>
    <div style="text-align: center; margin: 24px 0;">
      <a href="https://lumnos-companion.vercel.app" style="display: inline-block; background: linear-gradient(135deg, #4f46e5, #7c3aed);
         color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">
        Jetzt loslegen
      </a>
    </div>
    <p style="color: #6b7280; font-size: 14px;">Tipp: Starte mit dem IQ-Test um dein Niveau zu ermitteln!</p>
    """
    return await _send_email(to, f"Willkommen bei Lumnos, {username}!", _base_template(content))


async def send_password_reset_email(to: str, username: str, reset_token: str) -> bool:
    """Template 2: Password reset email."""
    content = f"""
    <h2 style="color: #1f2937;">Passwort zurücksetzen</h2>
    <p style="color: #4b5563; line-height: 1.6;">
      Hallo {username}, du hast ein neues Passwort angefordert.
    </p>
    <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; text-align: center; margin: 16px 0;">
      <p style="color: #374151; font-size: 14px; margin: 0 0 8px;">Dein Reset-Code:</p>
      <p style="color: #4f46e5; font-size: 28px; font-weight: bold; letter-spacing: 4px; margin: 0;">{reset_token}</p>
    </div>
    <p style="color: #6b7280; font-size: 14px;">
      Dieser Code ist 30 Minuten gueltig. Falls du kein Passwort-Reset angefordert hast, ignoriere diese Email.
    </p>
    """
    return await _send_email(to, "Passwort zurücksetzen - Lumnos", _base_template(content))


async def send_parent_link_email(
    to: str, parent_name: str, child_name: str, verify_token: str
) -> bool:
    """Template 3: Parent linking verification email."""
    content = f"""
    <h2 style="color: #1f2937;">Eltern-Verknüpfung bestätigen</h2>
    <p style="color: #4b5563; line-height: 1.6;">
      Hallo! <strong>{parent_name}</strong> möchte das Konto von <strong>{child_name}</strong> verknüpfen,
      um den Lernfortschritt zu verfolgen.
    </p>
    <div style="text-align: center; margin: 24px 0;">
      <a href="https://lumnos-companion.vercel.app/verify-parent?token={verify_token}" style="display: inline-block;
         background: #22c55e; color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none;
         font-weight: 600; margin-right: 12px;">
        Bestaetigen
      </a>
      <a href="https://lumnos-companion.vercel.app/reject-parent?token={verify_token}" style="display: inline-block;
         background: #ef4444; color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none;
         font-weight: 600;">
        Ablehnen
      </a>
    </div>
    <p style="color: #6b7280; font-size: 14px;">
      Wenn du diese Anfrage nicht kennst, ignoriere diese Email.
    </p>
    """
    return await _send_email(
        to,
        f"Eltern-Verknüpfung: {parent_name} möchte {child_name} verfolgen",
        _base_template(content),
    )


async def send_weekly_report_email(
    to: str,
    username: str,
    stats: dict,
) -> bool:
    """Template 4: Weekly learning report (sent every Monday)."""
    xp = stats.get("total_xp", 0)
    streak = stats.get("streak_days", 0)
    quizzes = stats.get("week_quizzes", 0)
    avg_score = stats.get("avg_quiz_score", 0)
    minutes = stats.get("week_learning_minutes", 0)
    strongest = stats.get("strongest_subjects", [])
    weakest = stats.get("weakest_subjects", [])

    strong_html = "".join(
        f"<span style='background:#dcfce7;color:#166534;padding:4px 8px;border-radius:4px;margin:2px;display:inline-block;font-size:13px;'>{s.get('subject', '')}: {s.get('avg_score', 0)}%</span>"
        for s in strongest[:3]
    ) or "<span style='color:#9ca3af;'>Noch keine Daten</span>"
    weak_html = "".join(
        f"<span style='background:#fee2e2;color:#991b1b;padding:4px 8px;border-radius:4px;margin:2px;display:inline-block;font-size:13px;'>{s.get('subject', '')}: {s.get('avg_score', 0)}%</span>"
        for s in weakest[:3]
    ) or "<span style='color:#9ca3af;'>Keine Schwächen erkannt</span>"

    content = f"""
    <h2 style="color: #1f2937;">Dein Wochen-Report</h2>
    <p style="color: #4b5563;">Hallo {username}! Hier ist deine Zusammenfassung:</p>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0;">
      <div style="background:#eff6ff;padding:16px;border-radius:8px;text-align:center;">
        <p style="color:#3b82f6;font-size:28px;font-weight:bold;margin:0;">{xp}</p>
        <p style="color:#6b7280;font-size:12px;margin:4px 0 0;">XP gesamt</p>
      </div>
      <div style="background:#fef3c7;padding:16px;border-radius:8px;text-align:center;">
        <p style="color:#f59e0b;font-size:28px;font-weight:bold;margin:0;">{streak}</p>
        <p style="color:#6b7280;font-size:12px;margin:4px 0 0;">Tage Streak</p>
      </div>
      <div style="background:#f0fdf4;padding:16px;border-radius:8px;text-align:center;">
        <p style="color:#22c55e;font-size:28px;font-weight:bold;margin:0;">{quizzes}</p>
        <p style="color:#6b7280;font-size:12px;margin:4px 0 0;">Quizze</p>
      </div>
      <div style="background:#faf5ff;padding:16px;border-radius:8px;text-align:center;">
        <p style="color:#a855f7;font-size:28px;font-weight:bold;margin:0;">{avg_score}%</p>
        <p style="color:#6b7280;font-size:12px;margin:4px 0 0;">Durchschnitt</p>
      </div>
    </div>
    <p style="color:#374151;font-weight:600;margin:16px 0 8px;">Stärkste Fächer:</p>
    <div>{strong_html}</div>
    <p style="color:#374151;font-weight:600;margin:16px 0 8px;">Zum Ueben:</p>
    <div>{weak_html}</div>
    <p style="color:#6b7280;font-size:13px;margin-top:20px;">Lernzeit: {minutes} Minuten diese Woche</p>
    """
    return await _send_email(
        to,
        f"Wochen-Report: {xp} XP, {quizzes} Quizze - Lumnos",
        _base_template(content),
    )


async def send_streak_loss_email(to: str, username: str, lost_streak: int) -> bool:
    """Template 5: Streak loss notification."""
    content = f"""
    <h2 style="color: #ef4444;">Streak verloren!</h2>
    <p style="color: #4b5563; line-height: 1.6;">
      Oh nein, {username}! Dein <strong>{lost_streak}-Tage Streak</strong> ist leider vorbei.
    </p>
    <div style="background: #fef2f2; padding: 20px; border-radius: 12px; text-align: center; margin: 16px 0;">
      <p style="font-size: 48px; margin: 0;">0</p>
      <p style="color: #991b1b; font-size: 14px; margin: 4px 0 0;">Neuer Streak</p>
    </div>
    <p style="color: #4b5563;">Aber keine Sorge! Starte heute neu und bau einen noch laengeren Streak auf.</p>
    <div style="text-align: center; margin: 20px 0;">
      <a href="https://lumnos-companion.vercel.app" style="display: inline-block; background: linear-gradient(135deg, #4f46e5, #7c3aed);
         color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">
        Jetzt neu starten
      </a>
    </div>
    """
    return await _send_email(
        to,
        f"Dein {lost_streak}-Tage Streak ist vorbei - Lumnos",
        _base_template(content),
    )


async def send_otp_code_email(to: str, code: str) -> bool:
    """Template 7: Email OTP / Magic Link verification code."""
    content = f"""
    <h2 style="color: #1f2937;">Dein Anmeldecode</h2>
    <p style="color: #4b5563; line-height: 1.6;">
      Hier ist dein Einmal-Code für LUMNOS. Gib diesen Code in der App ein:
    </p>
    <div style="background: linear-gradient(135deg, #eff6ff, #f0fdf4); padding: 24px; border-radius: 12px;
                text-align: center; margin: 20px 0; border: 2px dashed #6366f1;">
      <p style="color: #4f46e5; font-size: 36px; font-weight: bold; letter-spacing: 8px; margin: 0;
                font-family: 'Courier New', monospace;">{code}</p>
    </div>
    <p style="color: #6b7280; font-size: 14px;">
      Dieser Code ist <strong>15 Minuten</strong> gueltig. Falls du keinen Code angefordert hast, ignoriere diese E-Mail.
    </p>
    <p style="color: #9ca3af; font-size: 12px; margin-top: 16px;">
      Tipp: Kopiere den Code und fuege ihn in der App ein.
    </p>
    """
    return await _send_email(to, f"Dein LUMNOS Anmeldecode: {code}", _base_template(content))


async def send_tournament_winner_email(
    to: str, username: str, rank: int, subject: str, prize: str
) -> bool:
    """Template 6: Tournament winner congratulation."""
    medal = {1: "Gold", 2: "Silber", 3: "Bronze"}.get(rank, "")
    content = f"""
    <h2 style="color: #1f2937;">Glueckwunsch, {username}!</h2>
    <div style="background: linear-gradient(135deg, #fbbf24, #f59e0b); padding: 24px; border-radius: 12px;
                text-align: center; margin: 16px 0;">
      <p style="font-size: 48px; margin: 0;">{"&#127942;" if rank == 1 else "&#127941;" if rank == 2 else "&#127943;"}</p>
      <p style="color: #1f2937; font-size: 20px; font-weight: bold; margin: 8px 0;">Platz {rank} - {medal}</p>
      <p style="color: #374151; font-size: 14px; margin: 0;">{subject}-Turnier</p>
    </div>
    <div style="background: #f0fdf4; padding: 16px; border-radius: 8px; text-align: center; margin: 16px 0;">
      <p style="color: #166534; font-weight: 600; margin: 0;">Dein Preis: {prize}</p>
    </div>
    <p style="color: #4b5563;">Morgen gibt es ein neues Turnier. Sei wieder dabei!</p>
    """
    return await _send_email(
        to,
        f"Platz {rank} im {subject}-Turnier! - Lumnos",
        _base_template(content),
    )
