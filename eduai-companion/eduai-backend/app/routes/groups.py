"""Gruppen-Chats routes - WebSocket real-time group study (Max only).

Features:
- Create/join/leave study groups
- Real-time messaging via WebSocket
- @Lumnos mentions trigger KI responses via Groq
- Subject-based groups
- Max 10 members per group
"""
import json
import logging
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/groups", tags=["groups"])


async def ensure_default_group(db: aiosqlite.Connection) -> None:
    """Ensure the default 'Lumnos Community' group exists.

    Called at app startup or on first group list request.
    Creates the group with is_default=1 if it doesn't exist yet.
    """
    try:
        # Add is_default column if missing
        try:
            await db.execute("ALTER TABLE group_chats ADD COLUMN is_default INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass  # Column already exists

        cursor = await db.execute(
            "SELECT id FROM group_chats WHERE is_default = 1 AND is_active = 1 LIMIT 1"
        )
        if not await cursor.fetchone():
            await db.execute(
                """INSERT INTO group_chats (name, subject, created_by, members, is_active, is_default, max_members)
                VALUES ('🌟 Lumnos Community', 'Allgemein', 0, '[]', 1, 1, 9999)"""
            )
            await db.commit()
            logger.info("Created default group: Lumnos Community")
    except Exception as e:
        logger.warning("Could not ensure default group: %s", e)


async def join_default_group(user_id: int, db: aiosqlite.Connection) -> None:
    """Auto-join a user to the default Lumnos Community group if not already a member."""
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
        logger.debug("Could not auto-join default group for user %s: %s", user_id, e)


async def _get_user_tier(user_id: int, db: aiosqlite.Connection) -> str:
    """Get user's subscription tier."""
    cursor = await db.execute(
        "SELECT subscription_tier FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return (dict(row).get("subscription_tier", "free") or "free") if row else "free"


def _require_max_tier(user_tier: str) -> None:
    """Raise 403 if user is not on Max tier."""
    if user_tier != "max":
        raise HTTPException(
            status_code=403,
            detail="Gruppen-Chats sind nur für Max-Abonnenten verfügbar.",
        )


# Active WebSocket connections per group
active_connections: dict[int, list[WebSocket]] = {}


@router.get("/list")
async def list_groups(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List available study groups."""
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    cursor = await db.execute(
        """SELECT id, name, subject, created_by, members, max_members, is_active, created_at
        FROM group_chats WHERE is_active = 1
        ORDER BY created_at DESC LIMIT 20"""
    )
    rows = await cursor.fetchall()

    groups = []
    for r in rows:
        d = dict(r)
        members = json.loads(d.get("members", "[]"))
        groups.append({
            "id": d["id"],
            "name": d["name"],
            "subject": d["subject"],
            "member_count": len(members),
            "max_members": d["max_members"],
            "is_member": user_id in members,
            "created_at": d["created_at"],
        })

    return {"groups": groups}


@router.post("/create")
async def create_group(
    name: str,
    subject: str = "general",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new study group (Max only)."""
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    members = json.dumps([user_id])
    cursor = await db.execute(
        """INSERT INTO group_chats (name, subject, created_by, members)
        VALUES (?, ?, ?, ?)""",
        (name, subject, user_id, members),
    )
    await db.commit()
    group_id = cursor.lastrowid

    return {
        "group_id": group_id,
        "name": name,
        "subject": subject,
        "member_count": 1,
    }


@router.post("/{group_id}/join")
async def join_group(
    group_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Join an existing study group."""
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    cursor = await db.execute(
        "SELECT members, max_members FROM group_chats WHERE id = ? AND is_active = 1",
        (group_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gruppe nicht gefunden")

    d = dict(row)
    members = json.loads(d["members"])
    if user_id in members:
        return {"message": "Bereits Mitglied", "group_id": group_id}

    if len(members) >= d["max_members"]:
        raise HTTPException(status_code=400, detail="Gruppe ist voll")

    members.append(user_id)
    await db.execute(
        "UPDATE group_chats SET members = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(members), group_id),
    )
    await db.commit()

    return {"message": "Gruppe beigetreten", "group_id": group_id, "member_count": len(members)}


@router.post("/{group_id}/leave")
async def leave_group(
    group_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Leave a study group."""
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT members FROM group_chats WHERE id = ?", (group_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gruppe nicht gefunden")

    members = json.loads(dict(row)["members"])
    if user_id in members:
        members.remove(user_id)
        await db.execute(
            "UPDATE group_chats SET members = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(members), group_id),
        )
        await db.commit()

    return {"message": "Gruppe verlassen", "group_id": group_id}


@router.get("/{group_id}/messages")
async def get_group_messages(
    group_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get recent messages for a group."""
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    cursor = await db.execute(
        "SELECT messages FROM group_chats WHERE id = ? AND is_active = 1",
        (group_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gruppe nicht gefunden")

    messages = json.loads(dict(row)["messages"])
    # Return last 50 messages
    return {"messages": messages[-50:], "group_id": group_id}


@router.post("/{group_id}/send")
async def send_group_message(
    group_id: int,
    message: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Send a message to a group (REST fallback for WebSocket)."""
    user_id = current_user["id"]
    tier = await _get_user_tier(user_id, db)
    _require_max_tier(tier)

    cursor = await db.execute(
        "SELECT members, messages FROM group_chats WHERE id = ? AND is_active = 1",
        (group_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gruppe nicht gefunden")

    d = dict(row)
    members = json.loads(d["members"])
    if user_id not in members:
        raise HTTPException(status_code=403, detail="Du bist kein Mitglied dieser Gruppe")

    messages = json.loads(d["messages"])
    new_msg = {
        "user_id": user_id,
        "username": current_user.get("username", "Anonym"),
        "content": message,
        "timestamp": datetime.now().isoformat(),
    }
    messages.append(new_msg)

    # Keep only last 200 messages
    if len(messages) > 200:
        messages = messages[-200:]

    await db.execute(
        "UPDATE group_chats SET messages = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(messages, ensure_ascii=False), group_id),
    )
    await db.commit()

    # Broadcast to WebSocket connections
    if group_id in active_connections:
        msg_json = json.dumps(new_msg, ensure_ascii=False)
        disconnected = []
        for ws in active_connections[group_id]:
            try:
                await ws.send_text(msg_json)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            active_connections[group_id].remove(ws)

    return {"message": "Nachricht gesendet", "msg": new_msg}


async def _get_lumnos_response(text: str) -> str:
    """Get KI response from Groq when @Lumnos is mentioned."""
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return "Ich bin Lumnos! Leider ist gerade kein API-Key konfiguriert."

    try:
        import httpx
        # Remove @Lumnos from the text
        clean_text = text.replace("@Lumnos", "").replace("@lumnos", "").strip()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Du bist Lumnos, ein freundlicher KI-Lernhelfer in einem Gruppen-Chat. "
                                "Antworte kurz und hilfreich auf Deutsch. "
                                "Erkläre Konzepte einfach und gib Beispiele."
                            ),
                        },
                        {"role": "user", "content": clean_text},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("Groq call failed in group chat: %s", e)
    return "Entschuldigung, ich konnte gerade nicht antworten. Versuche es nochmal!"


@router.websocket("/ws/{group_id}")
async def websocket_group_chat(
    websocket: WebSocket,
    group_id: int,
):
    """WebSocket endpoint for real-time group chat.

    Supports @Lumnos mentions which trigger KI responses via Groq.
    """
    await websocket.accept()

    # Add to active connections
    if group_id not in active_connections:
        active_connections[group_id] = []
    active_connections[group_id].append(websocket)

    async def _broadcast(msg: dict) -> None:
        """Broadcast a message to all connections in this group."""
        text = json.dumps(msg, ensure_ascii=False)
        disconnected = []
        for ws in active_connections.get(group_id, []):
            try:
                await ws.send_text(text)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            if ws in active_connections.get(group_id, []):
                active_connections[group_id].remove(ws)

    try:
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            msg_data["timestamp"] = datetime.now().isoformat()

            # Broadcast user message
            await _broadcast(msg_data)

            # Check for @Lumnos mention → trigger KI response
            user_text = msg_data.get("content", "") or msg_data.get("text", "")
            if "@Lumnos" in user_text or "@lumnos" in user_text.lower():
                ki_response = await _get_lumnos_response(user_text)
                ki_msg = {
                    "user_id": 0,
                    "username": "Lumnos",
                    "content": ki_response,
                    "timestamp": datetime.now().isoformat(),
                    "is_ai": True,
                }
                await _broadcast(ki_msg)

    except WebSocketDisconnect:
        if group_id in active_connections and websocket in active_connections[group_id]:
            active_connections[group_id].remove(websocket)
