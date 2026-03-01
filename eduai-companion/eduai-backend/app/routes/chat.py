"""Chat routes - AI-powered tutoring conversations."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.schemas import ChatRequest, ChatResponse, ChatSessionResponse
from app.services.ai_engine import detect_subject, build_system_prompt
from app.services.groq_llm import call_groq_llm

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Send a message and get AI response."""
    user_id = current_user["id"]

    # Auto-detect subject if not specified
    detected_subject = detect_subject(request.message)
    subject = request.subject if request.subject and request.subject != "general" else detected_subject

    # Get user's proficiency for this subject
    cursor = await db.execute(
        "SELECT proficiency_level FROM learning_profiles WHERE user_id = ? AND subject = ?",
        (user_id, subject)
    )
    profile = await cursor.fetchone()
    level = dict(profile)["proficiency_level"] if profile else "intermediate"

    # Get or create session
    session_id = request.session_id
    if session_id:
        cursor = await db.execute(
            "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        )
        session = await cursor.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        messages = json.loads(dict(session)["messages"])
    else:
        # Create new session
        title = request.message[:50] + ("..." if len(request.message) > 50 else "")
        cursor = await db.execute(
            """INSERT INTO chat_sessions (user_id, subject, title, language, messages)
            VALUES (?, ?, ?, ?, '[]')""",
            (user_id, subject, title, request.language)
        )
        await db.commit()
        session_id = cursor.lastrowid
        messages = []

    # Add user message
    user_msg = {
        "role": "user",
        "content": request.message,
        "subject": subject,
        "timestamp": datetime.now().isoformat()
    }
    messages.append(user_msg)

    # Generate AI response via Groq LLM (falls back to template engine if no API key)
    system_prompt = build_system_prompt(
        subject=subject,
        level=level,
        language=request.language,
        detail_level=request.detail_level,
    )
    ai_response = call_groq_llm(
        prompt=request.message,
        system_prompt=system_prompt,
        subject=subject,
        level=level,
        language=request.language,
        chat_history=messages,
    )

    # Add assistant message
    assistant_msg = {
        "role": "assistant",
        "content": ai_response,
        "subject": subject,
        "timestamp": datetime.now().isoformat()
    }
    messages.append(assistant_msg)

    # Update session
    await db.execute(
        "UPDATE chat_sessions SET messages = ?, subject = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(messages, ensure_ascii=False), subject, session_id)
    )
    await db.commit()

    # Log activity
    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, subject, description)
        VALUES (?, 'chat', ?, ?)""",
        (user_id, subject, f"Asked about: {request.message[:100]}")
    )
    await db.commit()

    # Update last active
    await db.execute(
        "UPDATE learning_profiles SET last_active = datetime('now') WHERE user_id = ? AND subject = ?",
        (user_id, subject)
    )
    await db.commit()

    return ChatResponse(
        response=ai_response,
        session_id=session_id,
        subject=subject,
        detected_subject=detected_subject,
        proficiency_level=level
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """List all chat sessions for current user."""
    cursor = await db.execute(
        "SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC",
        (current_user["id"],)
    )
    sessions = await cursor.fetchall()

    return [
        ChatSessionResponse(
            id=dict(s)["id"],
            subject=dict(s)["subject"],
            title=dict(s)["title"],
            language=dict(s)["language"],
            message_count=len(json.loads(dict(s)["messages"])),
            created_at=dict(s)["created_at"],
            updated_at=dict(s)["updated_at"]
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Get a specific chat session with messages."""
    cursor = await db.execute(
        "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, current_user["id"])
    )
    session = await cursor.fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_dict = dict(session)
    return {
        "id": session_dict["id"],
        "subject": session_dict["subject"],
        "title": session_dict["title"],
        "language": session_dict["language"],
        "messages": json.loads(session_dict["messages"]),
        "created_at": session_dict["created_at"],
        "updated_at": session_dict["updated_at"]
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Delete a chat session."""
    cursor = await db.execute(
        "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, current_user["id"])
    )
    session = await cursor.fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    await db.commit()
    return {"message": "Session deleted"}
