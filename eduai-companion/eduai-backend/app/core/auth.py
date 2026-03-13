"""Authentication utilities.

Supports short-lived access tokens and long-lived refresh tokens.
Access tokens expire after ACCESS_TOKEN_EXPIRE_MINUTES (default 30 min).
Refresh tokens expire after REFRESH_TOKEN_EXPIRE_DAYS (default 7 days).

Supreme 13.0: Dual auth — supports both built-in JWT and Clerk OAuth tokens.
Clerk tokens (RS256) are verified via JWKS. Built-in tokens (HS256) are
verified with the local secret. The middleware tries Clerk first, then
falls back to built-in JWT.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiosqlite
from app.core.config import settings
from app.core.database import get_db

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived access token (default 30 min)."""
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a long-lived refresh token (default 7 days)."""
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Extract and validate user from JWT access token.

    Supreme 13.0: Dual auth — tries Clerk JWT first (RS256 via JWKS),
    then falls back to built-in JWT (HS256). This allows both Google/Apple
    OAuth users (via Clerk) and email/password users to authenticate.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # --- Dev-Token Bypass --- immer zuerst pruefen
    # Shield 7: In production, BLOCK dev-tokens completely
    if token == "dev-max-token-lumnos":
        if os.getenv("FLY_APP_NAME") or os.getenv("RAILWAY_ENVIRONMENT"):
            raise credentials_exception
        return {
            "id": 999,
            "username": "TestAdmin",
            "email": "admin@lumnos.de",
            "full_name": "Test Admin",
            "school_grade": "12",
            "school_type": "Gymnasium",
            "preferred_language": "de",
            "is_pro": 1,
            "subscription_tier": "max",
            "ki_personality_id": 1,
            "ki_personality_name": "Mentor",
            "avatar_url": "",
            "auth_provider": "dev",
            "created_at": "2024-01-01T00:00:00",
        }

    # --- Attempt 1: Clerk OAuth JWT (RS256) ---
    try:
        from app.core.clerk import verify_clerk_token, fetch_clerk_user, CLERK_ENABLED
        if CLERK_ENABLED:
            clerk_claims = await verify_clerk_token(token)
            if clerk_claims and clerk_claims.get("sub"):
                clerk_user_id = clerk_claims["sub"]
                # Step 1: Look up by clerk_user_id
                cursor = await db.execute(
                    "SELECT * FROM users WHERE clerk_user_id = ?", (clerk_user_id,)
                )
                user = await cursor.fetchone()
                if user:
                    user_d = dict(user)
                    # BUG 4 FIX: Enforce Max tier for owner emails at every Clerk auth
                    from app.routes.auth import is_admin, _ensure_admin_max_tier
                    if is_admin(user_d.get("email", "")):
                        await _ensure_admin_max_tier(db, user_d["id"])
                        user_d["subscription_tier"] = "max"
                        user_d["is_pro"] = 1
                        user_d["is_admin"] = 1
                    return user_d

                # Step 2: Clerk session JWTs don't contain email/name.
                # Fetch user details from Clerk Backend API.
                clerk_user_data = await fetch_clerk_user(clerk_user_id)
                email = ""
                full_name = ""
                avatar_url = ""
                username = ""
                if clerk_user_data:
                    email = clerk_user_data.get("email", "")
                    first = clerk_user_data.get("first_name", "")
                    last = clerk_user_data.get("last_name", "")
                    full_name = f"{first} {last}".strip() or (email.split("@")[0] if email else clerk_user_id)
                    avatar_url = clerk_user_data.get("image_url", "")
                    username = clerk_user_data.get("username", "") or (email.split("@")[0] if email else clerk_user_id)
                else:
                    # Fallback: use claims (may be empty)
                    email = clerk_claims.get("email", "")
                    full_name = clerk_claims.get("name", "") or (email.split("@")[0] if email else clerk_user_id)
                    username = email.split("@")[0] if email else clerk_user_id

                # Step 3: Check if email already exists (link accounts)
                if email:
                    cursor = await db.execute(
                        "SELECT * FROM users WHERE email = ?", (email,)
                    )
                    user = await cursor.fetchone()
                        if user:
                            # Link existing account to Clerk
                            await db.execute(
                                "UPDATE users SET clerk_user_id = ?, avatar_url = COALESCE(NULLIF(?, ''), avatar_url), auth_provider = 'clerk' WHERE email = ?",
                                (clerk_user_id, avatar_url, email),
                            )
                            await db.commit()
                            # Re-fetch to get updated row
                            cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
                            user = await cursor.fetchone()
                            if user:
                                user_d = dict(user)
                                # BUG 4 FIX: Enforce Max tier for owner emails at Clerk login
                                from app.routes.auth import is_admin, _ensure_admin_max_tier
                                if is_admin(user_d.get("email", "")):
                                    await _ensure_admin_max_tier(db, user_d["id"])
                                    user_d["subscription_tier"] = "max"
                                    user_d["is_pro"] = 1
                                    user_d["is_admin"] = 1
                                return user_d

                # Step 4: Auto-create new user from Clerk profile
                import secrets as _secrets
                dummy_password = get_password_hash(_secrets.token_urlsafe(32))
                await db.execute(
                    """INSERT INTO users (email, username, hashed_password, full_name, school_grade, school_type,
                    preferred_language, clerk_user_id, avatar_url, auth_provider)
                    VALUES (?, ?, ?, ?, '10', 'Gymnasium', 'de', ?, ?, 'clerk')""",
                    (email or f"{clerk_user_id}@clerk.local", username, dummy_password, full_name, clerk_user_id, avatar_url),
                )
                await db.commit()
                # Fetch the newly created user
                cursor = await db.execute(
                    "SELECT * FROM users WHERE clerk_user_id = ?", (clerk_user_id,)
                )
                user = await cursor.fetchone()
                if user:
                    import logging as _logging
                    _logging.getLogger(__name__).info(
                        "Auto-created user from Clerk: %s (email=%s)", clerk_user_id, email
                    )
                    user_d = dict(user)
                    # BUG 4 FIX: Enforce Max tier for owner emails at Clerk login
                    from app.routes.auth import is_admin, _ensure_admin_max_tier
                    if is_admin(user_d.get("email", "")):
                        await _ensure_admin_max_tier(db, user_d["id"])
                        user_d["subscription_tier"] = "max"
                        user_d["is_pro"] = 1
                        user_d["is_admin"] = 1
                    return user_d
    except HTTPException:
        raise  # Don't swallow auth exceptions
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).warning("Clerk auth attempt failed: %s", e)
        pass  # Fall through to built-in JWT

    # --- Attempt 2: Built-in JWT (HS256) ---
    try:
        payload = decode_token(token)
        # Accept both access tokens and legacy tokens (without type field)
        token_type = payload.get("type", "access")
        if token_type not in ("access",):
            raise credentials_exception
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = await cursor.fetchone()
    if user is None:
        raise credentials_exception

    return dict(user)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: aiosqlite.Connection = Depends(get_db),
) -> Optional[dict]:
    """Like get_current_user but returns None instead of 401 if no/bad token.

    Used for guest-accessible endpoints (e.g. guest chat).
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
