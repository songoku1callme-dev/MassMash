"""Authentication routes."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
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

router = APIRouter(prefix="/api/auth", tags=["auth"])

SUBJECTS = ["math", "english", "german", "history", "science"]


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
            is_pro=False,
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
            avatar_url=user_dict.get("avatar_url", "") or "",
            auth_provider=user_dict.get("auth_provider", "local") or "local",
            created_at=user_dict["created_at"]
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        username=current_user["username"],
        full_name=current_user["full_name"],
        school_grade=current_user["school_grade"],
        school_type=current_user["school_type"],
        preferred_language=current_user["preferred_language"],
        is_pro=bool(current_user.get("is_pro", 0)),
        avatar_url=current_user.get("avatar_url", "") or "",
        auth_provider=current_user.get("auth_provider", "local") or "local",
        created_at=current_user["created_at"]
    )


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
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        await db.execute(query, values)
        await db.commit()

    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],))
    user = dict(await cursor.fetchone())

    return UserResponse(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        full_name=user["full_name"],
        school_grade=user["school_grade"],
        school_type=user["school_type"],
        preferred_language=user["preferred_language"],
        is_pro=bool(user.get("is_pro", 0)),
        avatar_url=user.get("avatar_url", "") or "",
        auth_provider=user.get("auth_provider", "local") or "local",
        created_at=user["created_at"]
    )


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
