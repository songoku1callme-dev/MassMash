"""Authentication routes."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.models.schemas import UserRegister, UserLogin, TokenResponse, UserResponse, UserUpdate

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

    token = create_access_token(data={"sub": user_id})

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            school_grade=user.school_grade,
            school_type=user.school_type,
            preferred_language=user.preferred_language,
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
    token = create_access_token(data={"sub": user_dict["id"]})

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_dict["id"],
            email=user_dict["email"],
            username=user_dict["username"],
            full_name=user_dict["full_name"],
            school_grade=user_dict["school_grade"],
            school_type=user_dict["school_type"],
            preferred_language=user_dict["preferred_language"],
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
        created_at=user["created_at"]
    )
