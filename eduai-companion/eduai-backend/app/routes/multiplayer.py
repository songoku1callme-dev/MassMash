"""Multiplayer-Quiz routes - Real-time quiz duels via WebSocket.

Features:
- Create rooms with 6-char codes
- Up to 8 players per room
- Real-time scoring with speed bonus
- WebSocket broadcast for live updates
"""
import json
import logging
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.groq_llm import call_groq_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/multiplayer", tags=["multiplayer"])

# Active WebSocket connections per room
active_rooms: dict[str, list[dict]] = {}


def _generate_room_code() -> str:
    """Generate a 6-char alphanumeric room code."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(chars) for _ in range(6))


@router.post("/create-room")
async def create_room(
    subject: str = "general",
    topic: str = "",
    num_questions: int = 10,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new multiplayer quiz room."""
    user_id = current_user["id"]
    room_code = _generate_room_code()

    # Generate quiz questions via Groq
    questions = []
    try:
        prompt = f"Erstelle {num_questions} Multiple-Choice Quiz-Fragen zum Thema '{topic or subject}' fuer deutsche Gymnasialschueler. Format als JSON Array: [{{\"frage\": \"...\", \"optionen\": [\"A\", \"B\", \"C\", \"D\"], \"richtig\": 0, \"erklaerung\": \"...\"}}]. Nur das JSON Array, kein anderer Text."
        response = call_groq_llm(
            prompt=prompt,
            system_prompt="Du bist ein Quiz-Generator. Antworte NUR mit validem JSON.",
            subject=subject,
            level="intermediate",
            task_type="quiz_generation",
        )
        # Try to parse JSON from response
        try:
            # Find JSON array in response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                questions = json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
    except Exception as e:
        logger.warning("Failed to generate multiplayer questions: %s", e)

    if not questions:
        # Fallback questions
        questions = [
            {"frage": f"Beispielfrage {i+1} zu {topic or subject}", "optionen": ["A", "B", "C", "D"], "richtig": 0, "erklaerung": "Fallback-Frage"}
            for i in range(num_questions)
        ]

    players = [{"user_id": user_id, "username": current_user.get("username", "Host"), "score": 0, "answers": []}]

    cursor = await db.execute(
        """INSERT INTO multiplayer_rooms (room_code, host_id, subject, topic, num_questions, questions, players)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (room_code, user_id, subject, topic, num_questions, json.dumps(questions, ensure_ascii=False), json.dumps(players)),
    )
    await db.commit()

    return {
        "room_code": room_code,
        "room_id": cursor.lastrowid,
        "subject": subject,
        "topic": topic,
        "num_questions": len(questions),
        "players": players,
    }


@router.post("/join/{room_code}")
async def join_room(
    room_code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Join an existing multiplayer room."""
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM multiplayer_rooms WHERE room_code = ? AND status = 'waiting'",
        (room_code.upper(),),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden oder bereits gestartet")

    d = dict(row)
    players = json.loads(d["players"])

    if any(p["user_id"] == user_id for p in players):
        return {"message": "Bereits im Raum", "room_code": room_code, "players": players}

    if len(players) >= d["max_players"]:
        raise HTTPException(status_code=400, detail="Raum ist voll")

    players.append({"user_id": user_id, "username": current_user.get("username", "Spieler"), "score": 0, "answers": []})

    await db.execute(
        "UPDATE multiplayer_rooms SET players = ? WHERE room_code = ?",
        (json.dumps(players), room_code.upper()),
    )
    await db.commit()

    # Broadcast to WebSocket connections
    if room_code.upper() in active_rooms:
        msg = json.dumps({"type": "player_joined", "players": players})
        for conn in active_rooms[room_code.upper()]:
            try:
                await conn["ws"].send_text(msg)
            except Exception:
                pass

    return {"message": "Raum beigetreten", "room_code": room_code, "players": players, "num_questions": d["num_questions"]}


@router.post("/start/{room_code}")
async def start_quiz(
    room_code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Start the quiz (host only)."""
    cursor = await db.execute(
        "SELECT * FROM multiplayer_rooms WHERE room_code = ? AND host_id = ? AND status = 'waiting'",
        (room_code.upper(), current_user["id"]),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=403, detail="Nur der Host kann das Quiz starten")

    d = dict(row)
    questions = json.loads(d["questions"])

    await db.execute(
        "UPDATE multiplayer_rooms SET status = 'active' WHERE room_code = ?",
        (room_code.upper(),),
    )
    await db.commit()

    # Broadcast quiz start with first question (without correct answer)
    if room_code.upper() in active_rooms:
        safe_questions = []
        for q in questions:
            safe_questions.append({
                "frage": q["frage"],
                "optionen": q["optionen"],
            })
        msg = json.dumps({"type": "quiz_start", "questions": safe_questions, "total": len(questions)})
        for conn in active_rooms[room_code.upper()]:
            try:
                await conn["ws"].send_text(msg)
            except Exception:
                pass

    return {"message": "Quiz gestartet", "num_questions": len(questions)}


@router.post("/answer/{room_code}")
async def submit_answer(
    room_code: str,
    question_index: int,
    answer_index: int,
    time_seconds: float = 30.0,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit an answer for a multiplayer question."""
    user_id = current_user["id"]
    cursor = await db.execute(
        "SELECT * FROM multiplayer_rooms WHERE room_code = ? AND status = 'active'",
        (room_code.upper(),),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz nicht gefunden oder nicht aktiv")

    d = dict(row)
    questions = json.loads(d["questions"])
    players = json.loads(d["players"])

    if question_index >= len(questions):
        raise HTTPException(status_code=400, detail="Ungueltige Frage")

    question = questions[question_index]
    correct = question.get("richtig", 0)
    is_correct = answer_index == correct

    # Speed bonus: faster = more points (max 1000, min 100 if correct)
    points = 0
    if is_correct:
        speed_bonus = max(100, int(1000 * (1 - time_seconds / 30.0)))
        points = speed_bonus

    # Update player score
    for p in players:
        if p["user_id"] == user_id:
            p["score"] = p.get("score", 0) + points
            p["answers"] = p.get("answers", [])
            p["answers"].append({"q": question_index, "a": answer_index, "correct": is_correct, "points": points})
            break

    await db.execute(
        "UPDATE multiplayer_rooms SET players = ? WHERE room_code = ?",
        (json.dumps(players), room_code.upper()),
    )
    await db.commit()

    # Broadcast score update
    if room_code.upper() in active_rooms:
        scores = [{"username": p["username"], "score": p["score"]} for p in players]
        msg = json.dumps({"type": "score_update", "scores": scores, "question_index": question_index})
        for conn in active_rooms[room_code.upper()]:
            try:
                await conn["ws"].send_text(msg)
            except Exception:
                pass

    return {"correct": is_correct, "points": points, "correct_answer": correct, "erklaerung": question.get("erklaerung", "")}


@router.get("/room/{room_code}")
async def get_room(
    room_code: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get room status and players."""
    cursor = await db.execute(
        "SELECT * FROM multiplayer_rooms WHERE room_code = ?",
        (room_code.upper(),),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")

    d = dict(row)
    players = json.loads(d["players"])
    return {
        "room_code": d["room_code"],
        "subject": d["subject"],
        "topic": d["topic"],
        "status": d["status"],
        "host_id": d["host_id"],
        "players": players,
        "num_questions": d["num_questions"],
    }


@router.websocket("/ws/{room_code}")
async def multiplayer_websocket(websocket: WebSocket, room_code: str):
    """WebSocket for real-time multiplayer quiz updates."""
    await websocket.accept()
    code = room_code.upper()

    if code not in active_rooms:
        active_rooms[code] = []
    active_rooms[code].append({"ws": websocket})

    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast received data to all connections in room
            for conn in active_rooms.get(code, []):
                try:
                    if conn["ws"] != websocket:
                        await conn["ws"].send_text(data)
                except Exception:
                    pass
    except WebSocketDisconnect:
        if code in active_rooms:
            active_rooms[code] = [c for c in active_rooms[code] if c["ws"] != websocket]
            if not active_rooms[code]:
                del active_rooms[code]
