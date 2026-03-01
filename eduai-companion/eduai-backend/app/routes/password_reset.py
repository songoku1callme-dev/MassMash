"""Password reset and email verification using Resend API."""
import os
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_password_hash

router = APIRouter(prefix="/api/auth", tags=["password-reset"])

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = "noreply@eduai.de"


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


async def _ensure_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    await db.commit()


async def _send_email(to: str, subject: str, html: str) -> bool:
    """Send email via Resend API."""
    if not RESEND_API_KEY:
        return False
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                json={
                    "from": FROM_EMAIL,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
                timeout=10,
            )
            return resp.status_code == 200
    except Exception:
        return False


@router.post("/reset-password-request")
async def request_password_reset(
    req: PasswordResetRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Request a password reset email."""
    await _ensure_tables(db)

    cursor = await db.execute(
        "SELECT id, email FROM users WHERE email = ?", (req.email,)
    )
    user = await cursor.fetchone()

    # Always return success to prevent email enumeration
    if not user:
        return {"status": "ok", "message": "Falls ein Konto mit dieser E-Mail existiert, wurde ein Reset-Link gesendet."}

    user_dict = dict(user)
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(hours=1)).isoformat()

    await db.execute(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_dict["id"], token, expires),
    )
    await db.commit()

    reset_url = f"https://eduai.de/reset-password?token={token}"
    html = f"""
    <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
        <h2>Passwort zurücksetzen</h2>
        <p>Klicke auf den folgenden Link, um dein Passwort zurückzusetzen:</p>
        <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 8px;">
            Passwort zurücksetzen
        </a>
        <p style="color: #666; font-size: 14px; margin-top: 20px;">
            Dieser Link ist 1 Stunde gültig. Falls du kein Passwort-Reset angefordert hast, ignoriere diese E-Mail.
        </p>
    </div>
    """

    await _send_email(req.email, "EduAI - Passwort zurücksetzen", html)
    return {"status": "ok", "message": "Falls ein Konto mit dieser E-Mail existiert, wurde ein Reset-Link gesendet."}


@router.post("/reset-password")
async def reset_password(
    req: PasswordResetConfirm,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Reset password with token."""
    await _ensure_tables(db)

    cursor = await db.execute(
        "SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0",
        (req.token,),
    )
    token_row = await cursor.fetchone()
    if not token_row:
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Token")

    token_dict = dict(token_row)
    if datetime.fromisoformat(token_dict["expires_at"]) < datetime.now():
        raise HTTPException(status_code=400, detail="Token abgelaufen")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 6 Zeichen lang sein")

    hashed = get_password_hash(req.new_password)
    await db.execute(
        "UPDATE users SET hashed_password = ? WHERE id = ?",
        (hashed, token_dict["user_id"]),
    )
    await db.execute(
        "UPDATE password_reset_tokens SET used = 1 WHERE id = ?",
        (token_dict["id"],),
    )
    await db.commit()

    return {"status": "ok", "message": "Passwort erfolgreich geändert!"}
