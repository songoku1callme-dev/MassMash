"""Flashcards / Karteikarten with Spaced Repetition (SM-2 algorithm)."""
import json
import math
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.core.database import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


class FlashcardCreate(BaseModel):
    deck_name: str
    front: str
    back: str
    subject: str = "general"


class FlashcardReview(BaseModel):
    card_id: int
    quality: int  # 0-5 (SM-2 quality rating)


class DeckCreate(BaseModel):
    name: str
    subject: str = "general"
    description: str = ""


class AIGenerateRequest(BaseModel):
    topic: str
    count: int = 10
    subject: str = "general"
    deck_name: str = ""


async def _ensure_tables(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS flashcard_decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            subject TEXT DEFAULT 'general',
            description TEXT DEFAULT '',
            card_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER,
            user_id INTEGER NOT NULL,
            front TEXT NOT NULL DEFAULT '',
            back TEXT NOT NULL DEFAULT '',
            easiness REAL DEFAULT 2.5,
            interval INTEGER DEFAULT 1,
            repetitions INTEGER DEFAULT 0,
            next_review TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (deck_id) REFERENCES flashcard_decks(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # Migrate old schema: add deck_id column if missing
    try:
        cursor = await db.execute("PRAGMA table_info(flashcards)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "deck_id" not in columns:
            await db.execute("ALTER TABLE flashcards ADD COLUMN deck_id INTEGER REFERENCES flashcard_decks(id)")
        if "easiness" not in columns and "ease_factor" in columns:
            await db.execute("ALTER TABLE flashcards RENAME COLUMN ease_factor TO easiness")
        if "interval" not in columns and "interval_days" in columns:
            await db.execute("ALTER TABLE flashcards RENAME COLUMN interval_days TO interval")
    except Exception:
        pass  # Table just created with correct schema
    await db.commit()


def _sm2_update(easiness: float, interval: int, repetitions: int, quality: int) -> tuple[float, int, int]:
    """SM-2 spaced repetition algorithm."""
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * easiness)
        repetitions += 1

    new_easiness = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_easiness = max(1.3, new_easiness)
    return new_easiness, interval, repetitions


@router.get("/decks")
async def list_decks(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all flashcard decks for the current user."""
    await _ensure_tables(db)
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM flashcard_decks WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = await cursor.fetchall()
    decks = []
    for r in rows:
        d = dict(r)
        # Count due cards
        c = await db.execute(
            "SELECT COUNT(*) as cnt FROM flashcards WHERE deck_id = ? AND next_review <= datetime('now')",
            (d["id"],),
        )
        due = dict(await c.fetchone())["cnt"]
        d["due_count"] = due
        decks.append(d)
    return {"decks": decks}


@router.post("/decks")
async def create_deck(
    deck: DeckCreate,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new flashcard deck."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "INSERT INTO flashcard_decks (user_id, name, subject, description) VALUES (?, ?, ?, ?)",
        (current_user["id"], deck.name, deck.subject, deck.description),
    )
    await db.commit()
    return {"id": cursor.lastrowid, "name": deck.name}


@router.post("/cards")
async def create_card(
    card: FlashcardCreate,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new flashcard in a deck."""
    await _ensure_tables(db)
    user_id = current_user["id"]

    # Find or create deck
    cursor = await db.execute(
        "SELECT id FROM flashcard_decks WHERE user_id = ? AND name = ?",
        (user_id, card.deck_name),
    )
    deck_row = await cursor.fetchone()
    if deck_row:
        deck_id = dict(deck_row)["id"]
    else:
        cursor = await db.execute(
            "INSERT INTO flashcard_decks (user_id, name, subject) VALUES (?, ?, ?)",
            (user_id, card.deck_name, card.subject),
        )
        await db.commit()
        deck_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO flashcards (deck_id, user_id, front, back) VALUES (?, ?, ?, ?)",
        (deck_id, user_id, card.front, card.back),
    )
    await db.execute(
        "UPDATE flashcard_decks SET card_count = card_count + 1 WHERE id = ?",
        (deck_id,),
    )
    await db.commit()
    return {"id": cursor.lastrowid, "deck_id": deck_id}


@router.get("/review/{deck_id}")
async def get_review_cards(
    deck_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get cards due for review in a deck."""
    await _ensure_tables(db)
    cursor = await db.execute(
        """SELECT * FROM flashcards
        WHERE deck_id = ? AND user_id = ? AND next_review <= datetime('now')
        ORDER BY next_review ASC LIMIT 20""",
        (deck_id, current_user["id"]),
    )
    cards = [dict(r) for r in await cursor.fetchall()]
    return {"cards": cards, "count": len(cards)}


@router.post("/review")
async def review_card(
    review: FlashcardReview,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit a review for a flashcard (SM-2 algorithm)."""
    await _ensure_tables(db)
    cursor = await db.execute(
        "SELECT * FROM flashcards WHERE id = ? AND user_id = ?",
        (review.card_id, current_user["id"]),
    )
    card = await cursor.fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Karte nicht gefunden")

    card_dict = dict(card)
    quality = max(0, min(5, review.quality))
    new_e, new_i, new_r = _sm2_update(
        card_dict["easiness"], card_dict["interval"], card_dict["repetitions"], quality
    )
    next_review = (datetime.now() + timedelta(days=new_i)).isoformat()

    await db.execute(
        """UPDATE flashcards SET easiness = ?, interval = ?, repetitions = ?, next_review = ?
        WHERE id = ?""",
        (new_e, new_i, new_r, next_review, review.card_id),
    )
    await db.commit()
    return {"easiness": new_e, "interval": new_i, "next_review": next_review}


@router.post("/ai-generate")
async def ai_generate_cards(
    req: AIGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate flashcards using AI (Groq)."""
    await _ensure_tables(db)
    user_id = current_user["id"]

    from app.services.groq_llm import call_groq_llm

    prompt = f"""Erstelle genau {req.count} Karteikarten zum Thema "{req.topic}".

FORMAT: Antworte NUR mit einem JSON-Array:
[{{"front": "Frage/Begriff", "back": "Antwort/Definition"}}]

REGELN:
- Kurze, prägnante Fragen auf der Vorderseite
- Klare, vollständige Antworten auf der Rückseite
- Für deutsche Schüler (Klasse 5-13)
- Schwierigkeit variieren
- Keine Duplikate"""

    try:
        response = call_groq_llm(
            prompt=prompt,
            system_prompt="Du bist ein Experte für Lernmaterialien. Antworte NUR mit validem JSON.",
            subject=req.subject,
            level="intermediate",
            language="de",
            is_pro=True,
            temperature_override=0.3,
        )

        # Parse JSON
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        start = text.find("[")
        end = text.rfind("]")
        cards_data = json.loads(text[start:end + 1]) if start != -1 and end != -1 else []
    except Exception:
        # Fallback cards
        cards_data = [
            {"front": f"{req.topic} - Frage {i+1}", "back": f"Antwort zu {req.topic} #{i+1}"}
            for i in range(min(req.count, 5))
        ]

    deck_name = req.deck_name or f"{req.topic} (KI)"
    # Find or create deck
    cursor = await db.execute(
        "SELECT id FROM flashcard_decks WHERE user_id = ? AND name = ?",
        (user_id, deck_name),
    )
    deck_row = await cursor.fetchone()
    if deck_row:
        deck_id = dict(deck_row)["id"]
    else:
        cursor = await db.execute(
            "INSERT INTO flashcard_decks (user_id, name, subject) VALUES (?, ?, ?)",
            (user_id, deck_name, req.subject),
        )
        await db.commit()
        deck_id = cursor.lastrowid

    created = []
    for c in cards_data[:req.count]:
        front = c.get("front", "")
        back = c.get("back", "")
        if front and back:
            cur = await db.execute(
                "INSERT INTO flashcards (deck_id, user_id, front, back) VALUES (?, ?, ?, ?)",
                (deck_id, user_id, front, back),
            )
            created.append({"id": cur.lastrowid, "front": front, "back": back})

    await db.execute(
        "UPDATE flashcard_decks SET card_count = card_count + ? WHERE id = ?",
        (len(created), deck_id),
    )
    await db.commit()
    return {"deck_id": deck_id, "deck_name": deck_name, "cards": created, "count": len(created)}
