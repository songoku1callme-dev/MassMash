"""Authentication routes.

Shield 8: Account takeover protection — session management, password change invalidation.
"""
import json
import logging
import os
import secrets
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
import aiosqlite
from app.core.database import get_db
from app.core.auth import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user,
)
from app.models.schemas import (
    UserRegister, UserLogin, TokenResponse, UserResponse, UserUpdate,
    RefreshTokenRequest, RefreshTokenResponse,
)

from app.core.clerk import get_clerk_frontend_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Shield 8: In-memory session invalidation store
# Maps user_id -> timestamp; tokens issued before this time are invalid
_session_invalidation_store: dict[int, float] = {}

SUBJECTS = ["math", "english", "german", "history", "science"]

# Hardcoded admin whitelist — these users ALWAYS get permanent Max tier and can NEVER be downgraded
ADMIN_EMAILS = [
    "songoku1callme@gmail.com",
    "ahmadalkhalaf2019@gmail.com",
    "ahmadalkhalaf20024@gmail.com",
    "ahmadalkhalaf1245@gmail.com",
    "261g2g261@gmail.com",
    "261al3nzi261@gmail.com",
]


def is_admin(email: str) -> bool:
    """Check if an email belongs to a permanent admin."""
    return email.lower() in [e.lower() for e in ADMIN_EMAILS]


async def _ensure_admin_max_tier(db: aiosqlite.Connection, user_id: int) -> None:
    """Upgrade an admin user to Max tier. Called at login/register."""
    await db.execute(
        "UPDATE users SET subscription_tier = 'max', is_pro = 1, is_admin = 1 WHERE id = ?",
        (user_id,),
    )
    await db.commit()


async def seed_new_user(user_id: int, db: aiosqlite.Connection) -> None:
    """Seed demo content for a newly registered user.

    Creates:
    - 1 demo flashcard deck "Mathe Basics" with 3 cards
    - 1 welcome note explaining the app
    - Joins the default "Lumnos Community" group (if it exists)
    """
    try:
        # 1. Demo Flashcard Deck
        try:
            cursor = await db.execute(
                """INSERT INTO flashcard_decks (user_id, name, subject, description)
                VALUES (?, 'Mathe Basics', 'Mathematik', 'Grundlegende Mathe-Konzepte zum Einstieg')""",
                (user_id,),
            )
            await db.commit()
            deck_id = cursor.lastrowid
            demo_cards = [
                ("Was ist a² + b² = c²?", "Der Satz des Pythagoras — gilt für rechtwinklige Dreiecke. Die Summe der Quadrate der Katheten ergibt das Quadrat der Hypotenuse."),
                ("Was ist π (Pi)?", "π ≈ 3,14159 — das Verhältnis von Umfang zu Durchmesser eines Kreises. Wird in Geometrie und Trigonometrie verwendet."),
                ("Löse: 2x + 4 = 10", "x = 3. Rechnung: 2x = 10 - 4 = 6, also x = 6 ÷ 2 = 3."),
            ]
            for front, back in demo_cards:
                await db.execute(
                    """INSERT INTO flashcards (deck_id, user_id, front, back, subject)
                    VALUES (?, ?, ?, ?, 'Mathematik')""",
                    (deck_id, user_id, front, back),
                )
            await db.commit()
        except Exception as e:
            logger.debug("Could not seed flashcards for user %s: %s", user_id, e)

        # 2. Welcome Note
        try:
            await db.execute(
                """INSERT INTO notes (user_id, title, content, subject)
                VALUES (?, ?, ?, 'Allgemein')""",
                (user_id,
                 "🎉 Willkommen bei Lumnos!",
                 "# Willkommen bei Lumnos!\n\n"
                 "Hier kannst du deine Notizen speichern und organisieren.\n\n"
                 "## Tipps:\n"
                 "- **Fett** für wichtige Begriffe\n"
                 "- *Kursiv* für Definitionen\n"
                 "- `Code` für Formeln\n\n"
                 "## Was du als nächstes tun kannst:\n"
                 "1. Starte einen **KI-Chat** zu deinem Fach\n"
                 "2. Mach ein **Quiz** um dein Wissen zu testen\n"
                 "3. Erstelle **Karteikarten** für wichtige Begriffe\n"),
            )
            await db.commit()
        except Exception as e:
            logger.debug("Could not seed welcome note for user %s: %s", user_id, e)

        # 3. Join default group "Lumnos Community" (if it exists)
        try:
            cursor = await db.execute(
                "SELECT id, members FROM group_chats WHERE is_default = 1 AND is_active = 1 LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                d = dict(row)
                members = json.loads(d.get("members", "[]"))
                if user_id not in members:
                    members.append(user_id)
                    await db.execute(
                        "UPDATE group_chats SET members = ? WHERE id = ?",
                        (json.dumps(members), d["id"]),
                    )
                    await db.commit()
        except Exception as e:
            logger.debug("Could not join default group for user %s: %s", user_id, e)

    except Exception as e:
        logger.warning("seed_new_user failed for user %s: %s", user_id, e)


@router.post("/register", response_model=TokenResponse)
async def register(user: UserRegister, db: aiosqlite.Connection = Depends(get_db)):
    """Register a new user."""
    # Check if username or email exists
    cursor = await db.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (user.username, user.email)
    )
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    hashed_password = get_password_hash(user.password)
    cursor = await db.execute(
        """INSERT INTO users (email, username, hashed_password, full_name, school_grade, school_type, preferred_language)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user.email, user.username, hashed_password, user.full_name,
         user.school_grade, user.school_type, user.preferred_language)
    )
    await db.commit()
    user_id = cursor.lastrowid

    # Create learning profiles for all subjects
    for subject in SUBJECTS:
        await db.execute(
            """INSERT INTO learning_profiles (user_id, subject, proficiency_level, mastery_score)
            VALUES (?, ?, 'beginner', 0.0)""",
            (user_id, subject)
        )
    await db.commit()

    # Log activity
    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, description)
        VALUES (?, 'registration', 'Account created')""",
        (user_id,)
    )
    await db.commit()

    # Seed demo content for new user (flashcards, note, challenge)
    await seed_new_user(user_id, db)

    # Admin emails: always enforce Max tier at registration
    _is_admin = is_admin(user.email)
    _tier = "max" if _is_admin else "free"
    _is_pro = _is_admin
    if _is_admin:
        await _ensure_admin_max_tier(db, user_id)

    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            school_grade=user.school_grade,
            school_type=user.school_type,
            preferred_language=user.preferred_language,
            is_pro=_is_pro,
            subscription_tier=_tier,
            ki_personality_id=1,
            ki_personality_name="Freundlich",
            created_at=datetime.now().isoformat()
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: aiosqlite.Connection = Depends(get_db)):
    """Login and get access token."""
    cursor = await db.execute(
        "SELECT * FROM users WHERE username = ?", (credentials.username,)
    )
    user = await cursor.fetchone()

    if not user or not verify_password(credentials.password, dict(user)["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    user_dict = dict(user)

    # Admin emails: always enforce Max tier at login
    if is_admin(user_dict.get("email", "")):
        await _ensure_admin_max_tier(db, user_dict["id"])
        user_dict["subscription_tier"] = "max"
        user_dict["is_pro"] = 1
        user_dict["is_admin"] = 1

    # Auto-join default group on login (if not already member)
    try:
        from app.routes.groups import ensure_default_group, join_default_group
        await ensure_default_group(db)
        await join_default_group(user_dict["id"], db)
    except Exception:
        pass  # Non-critical

    access_token = create_access_token(data={"sub": user_dict["id"]})
    refresh_token = create_refresh_token(data={"sub": user_dict["id"]})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user_dict["id"],
            email=user_dict["email"],
            username=user_dict["username"],
            full_name=user_dict["full_name"],
            school_grade=user_dict["school_grade"],
            school_type=user_dict["school_type"],
            preferred_language=user_dict["preferred_language"],
            is_pro=bool(user_dict.get("is_pro", 0)),
            subscription_tier=user_dict.get("subscription_tier", "free") or "free",
            ki_personality_id=user_dict.get("ki_personality_id", 1) or 1,
            ki_personality_name=user_dict.get("ki_personality_name", "Freundlich") or "Freundlich",
            avatar_url=user_dict.get("avatar_url", "") or "",
            auth_provider=user_dict.get("auth_provider", "local") or "local",
            created_at=user_dict["created_at"]
        )
    )


def _user_response_from_dict(d: dict) -> UserResponse:
    """Build a UserResponse from a user row dict."""
    return UserResponse(
        id=d["id"],
        email=d["email"],
        username=d["username"],
        full_name=d["full_name"],
        school_grade=d["school_grade"],
        school_type=d["school_type"],
        preferred_language=d["preferred_language"],
        is_pro=bool(d.get("is_pro", 0)),
        subscription_tier=d.get("subscription_tier", "free") or "free",
        ki_personality_id=d.get("ki_personality_id", 1) or 1,
        ki_personality_name=d.get("ki_personality_name", "Freundlich") or "Freundlich",
        avatar_url=d.get("avatar_url", "") or "",
        auth_provider=d.get("auth_provider", "local") or "local",
        created_at=d["created_at"],
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return _user_response_from_dict(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    updates: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Update current user profile."""
    update_fields = []
    values = []

    if updates.full_name is not None:
        update_fields.append("full_name = ?")
        values.append(updates.full_name)
    if updates.school_grade is not None:
        update_fields.append("school_grade = ?")
        values.append(updates.school_grade)
    if updates.school_type is not None:
        update_fields.append("school_type = ?")
        values.append(updates.school_type)
    if updates.preferred_language is not None:
        update_fields.append("preferred_language = ?")
        values.append(updates.preferred_language)

    if update_fields:
        update_fields.append("updated_at = datetime('now')")
        values.append(current_user["id"])
        # Shield 4: Field names come from hardcoded Pydantic model checks above — NOT user input
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        await db.execute(query, values)
        await db.commit()

    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],))
    user = dict(await cursor.fetchone())

    return _user_response_from_dict(user)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Exchange a valid refresh token for a new access token."""
    from jose import JWTError
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token(data={"sub": user_id})
    return RefreshTokenResponse(access_token=new_access_token)


@router.post("/dev-bypass")
async def dev_bypass_login(db: aiosqlite.Connection = Depends(get_db)):
    """DEV BYPASS: Instantly login as the test user (Max-Tier) for testing.

    Shield 7: Only works when LUMNOS_DEV_MODE=1 is set AND FLY_APP_NAME is NOT set.
    This double-check prevents dev-mode from being accidentally enabled in production.
    Returns a real JWT token for the 'qualitytest' user (or creates one).
    """
    dev_mode = os.getenv("LUMNOS_DEV_MODE", "") == "1" or os.getenv("EDUAI_DEV_MODE", "") == "1"
    is_production = bool(os.getenv("FLY_APP_NAME")) or bool(os.getenv("RAILWAY_ENVIRONMENT"))

    # Shield 7: Never allow dev bypass in production, even if DEV_MODE is accidentally set
    if is_production or not dev_mode:
        raise HTTPException(status_code=403, detail="Dev bypass is disabled in production")

    # Find or create the test user
    cursor = await db.execute("SELECT * FROM users WHERE username = 'qualitytest'")
    user = await cursor.fetchone()

    if not user:
        # Create test user with Max tier
        hashed_pw = get_password_hash("Test1234!")
        cursor = await db.execute(
            """INSERT INTO users (email, username, hashed_password, full_name, school_grade,
            school_type, preferred_language, subscription_tier, is_pro)
            VALUES ('test@lumnos.de', 'qualitytest', ?, 'Quality Tester', '12', 'Gymnasium', 'de', 'max', 1)""",
            (hashed_pw,),
        )
        await db.commit()
        user_id = cursor.lastrowid
        # Create learning profiles
        for subject in SUBJECTS:
            await db.execute(
                "INSERT INTO learning_profiles (user_id, subject, proficiency_level, mastery_score) VALUES (?, ?, 'intermediate', 50.0)",
                (user_id, subject),
            )
        await db.commit()
    else:
        user_dict = dict(user)
        user_id = user_dict["id"]
        # Ensure Max tier
        await db.execute(
            "UPDATE users SET subscription_tier = 'max', is_pro = 1 WHERE id = ?",
            (user_id,),
        )
        await db.commit()

    # Re-fetch user
    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_dict = dict(await cursor.fetchone())

    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _user_response_from_dict(user_dict),
    }


@router.get("/clerk-config")
async def clerk_config():
    """Return Clerk OAuth configuration for the frontend.

    Returns whether Clerk is enabled and the publishable key (safe to expose).
    The frontend uses this to decide between Clerk login and built-in JWT login.
    """
    return get_clerk_frontend_config()


@router.post("/clerk/webhook")
async def clerk_webhook(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    """Handle Clerk webhook events to sync users to local DB.

    Events handled:
    - user.created → Create local user from Clerk profile
    - user.updated → Update local user profile
    """
    body = await request.json()
    event_type = body.get("type", "")
    data = body.get("data", {})

    if event_type in ("user.created", "user.updated"):
        clerk_user_id = data.get("id", "")
        email = ""
        emails = data.get("email_addresses", [])
        if emails:
            email = emails[0].get("email_address", "")
        first_name = data.get("first_name", "") or ""
        last_name = data.get("last_name", "") or ""
        full_name = f"{first_name} {last_name}".strip() or email.split("@")[0]
        avatar_url = data.get("image_url", "") or ""
        username = data.get("username", "") or email.split("@")[0] or clerk_user_id

        # Check if user already exists with this clerk_user_id
        cursor = await db.execute(
            "SELECT id FROM users WHERE clerk_user_id = ?", (clerk_user_id,)
        )
        existing = await cursor.fetchone()

        if existing:
            # Update existing user
            await db.execute(
                "UPDATE users SET full_name = ?, avatar_url = ?, email = ? WHERE clerk_user_id = ?",
                (full_name, avatar_url, email, clerk_user_id),
            )
        else:
            # Check if email already exists (link accounts)
            cursor = await db.execute("SELECT id FROM users WHERE email = ?", (email,))
            email_user = await cursor.fetchone()
            if email_user:
                await db.execute(
                    "UPDATE users SET clerk_user_id = ?, avatar_url = ?, auth_provider = 'clerk' WHERE email = ?",
                    (clerk_user_id, avatar_url, email),
                )
            else:
                # Create new user
                import secrets
                dummy_password = get_password_hash(secrets.token_urlsafe(32))
                await db.execute(
                    """INSERT INTO users (email, username, hashed_password, full_name, school_grade, school_type,
                    preferred_language, clerk_user_id, avatar_url, auth_provider)
                    VALUES (?, ?, ?, ?, '10', 'Gymnasium', 'de', ?, ?, 'clerk')""",
                    (email, username, dummy_password, full_name, clerk_user_id, avatar_url),
                )
                # Create learning profiles
                user_id = (await db.execute("SELECT last_insert_rowid()")).fetchone()
                if user_id:
                    uid = dict(user_id)[list(dict(user_id).keys())[0]] if user_id else None
                    if uid:
                        for subject in SUBJECTS:
                            await db.execute(
                                """INSERT INTO learning_profiles (user_id, subject, proficiency_level, mastery_score)
                                VALUES (?, ?, 'beginner', 0.0)""",
                                (uid, subject),
                            )
        await db.commit()

    return {"status": "ok"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOCK 3: Email OTP (Magic Link / Code) — Bot-Schutz
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# In-memory OTP store: {email: {"code": "123456", "expires": timestamp}}
_otp_store: dict[str, dict] = {}
OTP_EXPIRY_SECONDS = 900  # 15 minutes
OTP_COOLDOWN_SECONDS = 60  # 1 minute between sends


class OTPSendRequest(BaseModel):
    email: str  # Using str instead of EmailStr to avoid pydantic[email] dependency


class OTPVerifyRequest(BaseModel):
    email: str
    code: str


@router.post("/send-magic-link")
async def send_magic_link(req: OTPSendRequest, db: aiosqlite.Connection = Depends(get_db)):
    """Send a 6-digit OTP code to the given email via Resend.

    - Generates a random 6-digit code
    - Stores it in-memory with 15 min expiry
    - Sends a styled HTML email via Resend API
    - Rate-limited: 1 send per 60 seconds per email
    """
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Ungueltige E-Mail-Adresse.")

    # Rate limit: check cooldown
    existing = _otp_store.get(email)
    if existing:
        elapsed = time.time() - existing.get("created_at", 0)
        if elapsed < OTP_COOLDOWN_SECONDS:
            remaining = int(OTP_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Bitte warte {remaining} Sekunden bevor du einen neuen Code anforderst.",
            )

    # Generate 6-digit code
    code = f"{secrets.randbelow(900000) + 100000}"

    # Store with expiry
    _otp_store[email] = {
        "code": code,
        "expires": time.time() + OTP_EXPIRY_SECONDS,
        "created_at": time.time(),
        "attempts": 0,
    }

    # Send email via Resend
    from app.services.email_service import send_otp_code_email
    sent = await send_otp_code_email(email, code)

    return {
        "success": True,
        "message": "Code wurde gesendet." if sent else "Code generiert (E-Mail-Versand deaktiviert).",
        "email_sent": sent,
        # Shield 7: Only return dev_code if dev mode AND not production
        "dev_code": code if (os.getenv("LUMNOS_DEV_MODE") == "1" and not os.getenv("FLY_APP_NAME")) else None,
    }


@router.post("/verify-code")
async def verify_code(req: OTPVerifyRequest, db: aiosqlite.Connection = Depends(get_db)):
    """Verify a 6-digit OTP code and return a JWT token.

    - Validates the code against the in-memory store
    - On success: finds or creates the user, returns JWT tokens
    - On failure: increments attempt counter (max 5 attempts)
    - After verification: deletes the OTP entry
    """
    email = req.email.strip().lower()
    code = req.code.strip()

    if not email or not code:
        raise HTTPException(status_code=400, detail="E-Mail und Code sind erforderlich.")

    # Look up OTP
    entry = _otp_store.get(email)
    if not entry:
        raise HTTPException(status_code=404, detail="Kein Code für diese E-Mail gefunden. Fordere einen neuen an.")

    # Check expiry
    if time.time() > entry["expires"]:
        del _otp_store[email]
        raise HTTPException(status_code=410, detail="Code abgelaufen. Fordere einen neuen an.")

    # Check max attempts (brute-force protection)
    if entry["attempts"] >= 5:
        del _otp_store[email]
        raise HTTPException(status_code=429, detail="Zu viele Versuche. Fordere einen neuen Code an.")

    # Verify code
    entry["attempts"] += 1
    if entry["code"] != code:
        remaining = 5 - entry["attempts"]
        raise HTTPException(
            status_code=401,
            detail=f"Falscher Code. Noch {remaining} Versuche.",
        )

    # Success — delete OTP entry
    del _otp_store[email]

    # Find or create user
    cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = await cursor.fetchone()

    if user:
        user_dict = dict(user)
        user_id = user_dict["id"]
        # Admin check
        if is_admin(email):
            await _ensure_admin_max_tier(db, user_id)
            user_dict["subscription_tier"] = "max"
            user_dict["is_pro"] = 1
    else:
        # Create new user from email
        username = email.split("@")[0]
        # Ensure unique username
        cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
        if await cursor.fetchone():
            username = f"{username}_{secrets.randbelow(9999)}"

        hashed_pw = get_password_hash(secrets.token_urlsafe(32))
        _is_admin = is_admin(email)
        _tier = "max" if _is_admin else "free"

        cursor = await db.execute(
            """INSERT INTO users (email, username, hashed_password, full_name, school_grade,
            school_type, preferred_language, subscription_tier, is_pro, auth_provider)
            VALUES (?, ?, ?, ?, '10', 'Gymnasium', 'de', ?, ?, 'email_otp')""",
            (email, username, hashed_pw, username, _tier, int(_is_admin)),
        )
        await db.commit()
        user_id = cursor.lastrowid

        # Create learning profiles
        for subject in SUBJECTS:
            await db.execute(
                "INSERT INTO learning_profiles (user_id, subject, proficiency_level, mastery_score) VALUES (?, ?, 'beginner', 0.0)",
                (user_id, subject),
            )
        await db.commit()

        if _is_admin:
            await _ensure_admin_max_tier(db, user_id)

        # Re-fetch
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_dict = dict(await cursor.fetchone())

    # Generate tokens
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _user_response_from_dict(user_dict),
        "is_new_user": user is None,
    }


# ---------------------------------------------------------------------------
# Shield 8: Account Takeover Protection — Session Management
# ---------------------------------------------------------------------------


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Shield 8: Change password and invalidate all other sessions.

    Requires old password confirmation. After change, all existing
    tokens become invalid — user must re-login on all devices.
    """
    user_id = current_user["id"]

    # Fetch current password hash
    cursor = await db.execute(
        "SELECT password_hash FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    row_dict = dict(row)
    if not verify_password(req.old_password, row_dict.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Altes Passwort ist falsch")

    # Validate new password
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Neues Passwort muss mindestens 8 Zeichen lang sein")
    if len(req.new_password) > 128:
        raise HTTPException(status_code=400, detail="Neues Passwort darf maximal 128 Zeichen lang sein")

    # Update password
    new_hash = get_password_hash(req.new_password)
    await db.execute(
        "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
        (new_hash, user_id),
    )
    await db.commit()

    # Invalidate all sessions — tokens issued before now are invalid
    _session_invalidation_store[user_id] = time.time()

    logger.info("Shield 8: Password changed for user_id=%s, all sessions invalidated", user_id)

    # Issue new tokens for the current session
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return {
        "message": "Passwort geaendert. Alle anderen Sessions wurden abgemeldet.",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.delete("/account")
@router.post("/account/delete")  # POST fallback for proxies that block DELETE
async def delete_account(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Konto dauerhaft löschen — alle Daten werden entfernt.

    Löscht den User und alle zugehörigen Daten aus der Datenbank.
    Optional: Clerk-User wird ebenfalls gelöscht (wenn Clerk aktiv).
    Owner/Admin-Accounts können sich AUCH löschen (eigene Entscheidung).
    """
    user_id = current_user["id"]
    user_email = current_user.get("email", "")
    clerk_id = current_user.get("clerk_user_id", "") or current_user.get("clerk_id", "")

    logger.info("Account deletion requested for user_id=%s email=%s", user_id, user_email)

    # Alle User-Daten löschen (umfassende Liste)
    tables_to_clean = [
        "chat_messages", "chat_sessions",
        "quiz_results", "gamification",
        "flashcards", "flashcard_decks", "notes", "xp_log",
        "daily_quests", "activity_log",
        "user_memories", "learning_profiles",
        "pomodoro_sessions", "referrals",
        "coupon_redemptions", "tournament_entries", "admin_logs",
        "battle_pass", "battle_pass_progress",
        "iq_results", "abitur_simulations",
        "notifications", "shop_purchases",
    ]
    for table in tables_to_clean:
        try:
            await db.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
        except Exception:
            pass  # Tabelle existiert möglicherweise nicht

    # Lösche den User selbst
    await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    await db.commit()

    # Clerk User löschen (optional, kein Crash)
    try:
        clerk_secret = os.getenv("CLERK_SECRET_KEY", "")
        if clerk_id and clerk_secret:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.delete(
                    f"https://api.clerk.com/v1/users/{clerk_id}",
                    headers={"Authorization": f"Bearer {clerk_secret}"},
                )
    except Exception as e:
        logger.warning("Clerk user deletion failed (non-fatal): %s", e)

    logger.info("Account deleted: user_id=%s", user_id)
    return {"message": "Account gelöscht"}


@router.get("/sessions")
async def list_sessions(
    current_user: dict = Depends(get_current_user),
):
    """Shield 8: Show active session info for the user.

    Note: With JWT tokens, we track invalidation timestamps rather than
    individual sessions. This endpoint shows when sessions were last invalidated.
    """
    user_id = current_user["id"]
    last_invalidation = _session_invalidation_store.get(user_id)

    return {
        "user_id": user_id,
        "current_session": "active",
        "last_invalidation": datetime.fromtimestamp(last_invalidation).isoformat() if last_invalidation else None,
        "note": "JWT-basierte Sessions. Passwort-Änderung invalidiert alle anderen Sessions.",
    }


@router.delete("/sessions/all")
async def logout_all_sessions(
    current_user: dict = Depends(get_current_user),
):
    """Shield 8: Invalidate all sessions except the current one.

    All tokens issued before this moment become invalid.
    The current user gets new tokens.
    """
    user_id = current_user["id"]
    _session_invalidation_store[user_id] = time.time()

    logger.info("Shield 8: All sessions invalidated for user_id=%s", user_id)

    # Issue new tokens for the current session
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return {
        "message": "Alle anderen Sessions wurden abgemeldet.",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
