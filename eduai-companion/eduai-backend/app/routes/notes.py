"""Notizen-System with Markdown editor and AI enhancement."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteCreate(BaseModel):
    title: str
    content: str
    subject: str = "general"


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    subject: str | None = None


class AIEnhanceRequest(BaseModel):
    note_id: int
    action: str = "improve"  # improve, summarize, quiz, flashcards


async def _ensure_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            subject TEXT DEFAULT 'general',
            word_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    await db.commit()


@router.get("/")
async def list_notes(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all notes for the current user."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "SELECT id, title, subject, word_count, created_at, updated_at FROM notes WHERE user_id = ? ORDER BY updated_at DESC",
        (current_user["id"],),
    )
    notes = [dict(r) for r in await cursor.fetchall()]
    return {"notes": notes}


@router.get("/{note_id}")
async def get_note(
    note_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get a single note."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?",
        (note_id, current_user["id"]),
    )
    note = await cursor.fetchone()
    if not note:
        raise HTTPException(status_code=404, detail="Notiz nicht gefunden")
    return dict(note)


@router.post("/")
async def create_note(
    note: NoteCreate,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new note."""
    await _ensure_tables(db)
    word_count = len(note.content.split())
    cursor = await db.execute(
        "INSERT INTO notes (user_id, title, content, subject, word_count) VALUES (?, ?, ?, ?, ?)",
        (current_user["id"], note.title, note.content, note.subject, word_count),
    )
    await db.commit()
    return {"id": cursor.lastrowid, "title": note.title}


@router.put("/{note_id}")
async def update_note(
    note_id: int,
    updates: NoteUpdate,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Update a note."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?",
        (note_id, current_user["id"]),
    )
    existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Notiz nicht gefunden")

    fields = []
    values = []
    if updates.title is not None:
        fields.append("title = ?")
        values.append(updates.title)
    if updates.content is not None:
        fields.append("content = ?")
        values.append(updates.content)
        fields.append("word_count = ?")
        values.append(len(updates.content.split()))
    if updates.subject is not None:
        fields.append("subject = ?")
        values.append(updates.subject)

    if fields:
        fields.append("updated_at = datetime('now')")
        values.append(note_id)
        # Shield 4: Field names come from hardcoded Pydantic model above — NOT user input
        await db.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id = ?", values)
        await db.commit()

    return {"status": "updated"}


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Delete a note."""
    await _ensure_tables(db)
    await db.execute(
        "DELETE FROM notes WHERE id = ? AND user_id = ?",
        (note_id, current_user["id"]),
    )
    await db.commit()
    return {"status": "deleted"}


@router.post("/ai-enhance")
async def ai_enhance_note(
    req: AIEnhanceRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Enhance a note using AI."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?",
        (req.note_id, current_user["id"]),
    )
    note = await cursor.fetchone()
    if not note:
        raise HTTPException(status_code=404, detail="Notiz nicht gefunden")

    note_dict = dict(note)
    from app.routes.chat import call_groq_llm

    prompts = {
        "improve": f"Verbessere diese Notiz sprachlich und inhaltlich. Behalte die Kernaussagen bei:\n\n{note_dict['content']}",
        "summarize": f"Fasse diese Notiz in 3-5 Stichpunkten zusammen:\n\n{note_dict['content']}",
        "quiz": f"Erstelle 5 Quiz-Fragen basierend auf dieser Notiz. Format: JSON-Array mit {{\"frage\": \"...\", \"antwort\": \"...\"}}:\n\n{note_dict['content']}",
        "flashcards": f"Erstelle 5 Karteikarten aus dieser Notiz. Format: JSON-Array mit {{\"front\": \"...\", \"back\": \"...\"}}:\n\n{note_dict['content']}",
    }

    prompt = prompts.get(req.action, prompts["improve"])

    try:
        result = call_groq_llm(
            prompt=prompt,
            system_prompt="Du bist ein Lernassistent. Hilf Schülern ihre Notizen zu verbessern.",
            subject=note_dict.get("subject", "general"),
            level="intermediate",
            language="de",
            is_pro=True,
        )
        return {"action": req.action, "result": result}
    except Exception as e:
        return {"action": req.action, "result": f"KI-Verbesserung nicht verfügbar: {e}", "error": True}
