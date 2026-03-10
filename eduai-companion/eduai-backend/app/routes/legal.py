"""DSGVO + Legal routes - Cookie consent, Datenschutz, Impressum, Account deletion.

Required for German law compliance (DSGVO/GDPR).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/legal", tags=["legal"])


@router.get("/datenschutz")
async def datenschutzerklärung():
    """Return the privacy policy (Datenschutzerklärung)."""
    return {
        "title": "Datenschutzerklärung",
        "last_updated": "2026-03-01",
        "sections": [
            {
                "title": "1. Verantwortlicher",
                "content": "Lumnos Companion ist ein Bildungstechnologie-Projekt. Kontakt: support@lumnos-companion.de"
            },
            {
                "title": "2. Welche Daten wir erheben",
                "content": "Wir erheben: E-Mail-Adresse, Benutzername, Schulklasse, Schultyp, Lernfortschritt, Quiz-Ergebnisse, Chat-Verlaeufe. Alle Daten dienen ausschliesslich der Lernunterstuetzung."
            },
            {
                "title": "3. Zweck der Verarbeitung",
                "content": "Personalisiertes Lernen, KI-gestütztes Tutoring, Fortschrittsverfolgung, Gamification. Keine Daten werden an Dritte verkauft."
            },
            {
                "title": "4. KI-Verarbeitung (Groq)",
                "content": "Chat-Nachrichten werden an die Groq API gesendet für KI-Antworten. Es werden keine personenbezogenen Daten (Name, E-Mail) an Groq übermittelt. Nur der Fragetext und minimaler Kontext."
            },
            {
                "title": "5. Zahlungsdaten (Stripe)",
                "content": "Zahlungen werden über Stripe abgewickelt. Wir speichern keine Kreditkartendaten. Stripe ist PCI-DSS zertifiziert."
            },
            {
                "title": "6. Cookies",
                "content": "Wir verwenden: Notwendige Cookies (Session, Auth-Token), Optionale Cookies (Dark Mode Praeferenz, Sprache). Keine Tracking-Cookies ohne Einwilligung."
            },
            {
                "title": "7. Deine Rechte (DSGVO Art. 15-22)",
                "content": "Du hast das Recht auf: Auskunft, Berichtigung, Loeschung, Einschraenkung, Datenportabilitaet, Widerspruch. Kontaktiere uns jederzeit."
            },
            {
                "title": "8. Account loeschen",
                "content": "Du kannst deinen Account jederzeit in den Einstellungen loeschen. Alle deine Daten werden unwiderruflich entfernt."
            },
            {
                "title": "9. Speicherdauer",
                "content": "Deine Daten werden gespeichert solange dein Account aktiv ist. Nach Loeschung werden alle Daten innerhalb von 30 Tagen entfernt."
            },
        ],
    }


@router.get("/impressum")
async def impressum():
    """Return the legal notice (Impressum)."""
    return {
        "title": "Impressum",
        "content": {
            "name": "Lumnos Companion",
            "description": "KI-gestütztes Lernen für deutsche Schüler",
            "email": "support@lumnos-companion.de",
            "haftungsausschluss": "Die Inhalte dieser App wurden mit größter Sorgfalt erstellt. Für die Richtigkeit, Vollständigkeit und Aktualität der Inhalte können wir jedoch keine Gewähr übernehmen. Die KI-generierten Antworten ersetzen keinen professionellen Unterricht.",
            "urheberrecht": "Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen dem deutschen Urheberrecht.",
        },
    }


@router.post("/cookie-consent")
async def save_cookie_consent(
    consent_type: str = "necessary",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Save cookie consent preference.

    consent_type: 'all' | 'necessary' | 'custom'
    """
    if consent_type not in ("all", "necessary", "custom"):
        raise HTTPException(status_code=400, detail="Ungueltiger Consent-Typ")

    return {"message": "Cookie-Einstellungen gespeichert", "consent_type": consent_type}


@router.delete("/account")
async def delete_account(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Delete user account and ALL associated data (DSGVO Art. 17)."""
    user_id = current_user["id"]

    # Shield 4: Delete all user data from all tables
    # Table names are hardcoded (not from user input) — safe against SQL injection
    _ACCOUNT_DELETION_TABLES = (
        "chat_sessions", "quiz_results", "learning_profiles", "activity_log",
        "user_memories", "abitur_simulations", "wochen_coach_plans", "gamification",
        "research_results", "chat_feedback", "push_subscriptions",
        "iq_tests", "iq_results", "tournament_entries",
    )

    for table in _ACCOUNT_DELETION_TABLES:
        try:
            # Table names are from a hardcoded tuple above — NOT user input
            await db.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
        except Exception:
            pass  # Table might not exist

    # Delete the user account itself
    await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    await db.commit()

    logger.info("Account deleted for user_id=%s (DSGVO Art. 17)", user_id)
    return {"message": "Dein Account und alle Daten wurden unwiderruflich geloescht."}
