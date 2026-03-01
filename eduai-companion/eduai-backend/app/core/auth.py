"""Authentication utilities.

Supports short-lived access tokens and long-lived refresh tokens.
Access tokens expire after ACCESS_TOKEN_EXPIRE_MINUTES (default 30 min).
Refresh tokens expire after REFRESH_TOKEN_EXPIRE_DAYS (default 7 days).

Supreme 13.0: Dual auth — supports both built-in JWT and Clerk OAuth tokens.
Clerk tokens (RS256) are verified via JWKS. Built-in tokens (HS256) are
verified with the local secret. The middleware tries Clerk first, then
falls back to built-in JWT.
"""
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

    # --- Attempt 1: Clerk OAuth JWT (RS256) ---
    try:
        from app.core.clerk import verify_clerk_token, CLERK_ENABLED
        if CLERK_ENABLED:
            clerk_claims = await verify_clerk_token(token)
            if clerk_claims and clerk_claims.get("sub"):
                clerk_user_id = clerk_claims["sub"]
                cursor = await db.execute(
                    "SELECT * FROM users WHERE clerk_user_id = ?", (clerk_user_id,)
                )
                user = await cursor.fetchone()
                if user:
                    return dict(user)
                # Auto-create user from Clerk claims (first login)
                email = clerk_claims.get("email", "")
                name = clerk_claims.get("name", "") or email.split("@")[0]
                if email:
                    # Check if email already exists
                    cursor = await db.execute(
                        "SELECT * FROM users WHERE email = ?", (email,)
                    )
                    user = await cursor.fetchone()
                    if user:
                        # Link existing account to Clerk
                        await db.execute(
                            "UPDATE users SET clerk_user_id = ?, auth_provider = 'clerk' WHERE email = ?",
                            (clerk_user_id, email),
                        )
                        await db.commit()
                        return dict(user)
    except Exception:
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
