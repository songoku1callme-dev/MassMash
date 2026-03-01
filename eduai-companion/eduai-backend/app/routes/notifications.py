"""Push Notifications + Weekly Report routes.

Supreme 10.0 Phase 2: VAPID push + APScheduler triggers + Resend email.
Supreme 13.0 Phase 7: WebSocket real-time notifications (replaces polling).
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/bell")
async def get_notification_bell(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get unread notifications for the bell icon (Supreme 12.0 Phase 7)."""
    user_id = current_user["id"]

    # Get unread count
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
        (user_id,),
    )
    row = await cursor.fetchone()
    unread_count = dict(row)["cnt"] if row else 0

    # Get last 20 notifications
    cursor = await db.execute(
        """SELECT id, title, message, notification_type, is_read, created_at
        FROM notifications WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 20""",
        (user_id,),
    )
    rows = await cursor.fetchall()
    items = []
    for r in rows:
        rd = dict(r)
        items.append({
            "id": rd["id"],
            "title": rd.get("title", ""),
            "message": rd.get("message", ""),
            "type": rd.get("notification_type", "info"),
            "is_read": bool(rd.get("is_read", 0)),
            "created_at": rd.get("created_at", ""),
        })

    return {"unread_count": unread_count, "notifications": items}


@router.post("/mark-read/{notification_id}")
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Mark a single notification as read."""
    user_id = current_user["id"]
    await db.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
        (notification_id, user_id),
    )
    await db.commit()
    return {"message": "Gelesen"}


@router.post("/mark-all-read")
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Mark all notifications as read."""
    user_id = current_user["id"]
    await db.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
        (user_id,),
    )
    await db.commit()
    return {"message": "Alle gelesen"}


@router.post("/subscribe")
async def subscribe_push(
    endpoint: str,
    p256dh: str = "",
    auth_key: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Subscribe to push notifications."""
    user_id = current_user["id"]

    await db.execute(
        """INSERT OR REPLACE INTO push_subscriptions (user_id, endpoint, p256dh, auth_key)
        VALUES (?, ?, ?, ?)""",
        (user_id, endpoint, p256dh, auth_key),
    )
    await db.commit()

    return {"message": "Push-Benachrichtigungen aktiviert!"}


@router.delete("/unsubscribe")
async def unsubscribe_push(
    endpoint: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Unsubscribe from push notifications."""
    user_id = current_user["id"]
    await db.execute(
        "DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
        (user_id, endpoint),
    )
    await db.commit()
    return {"message": "Push-Benachrichtigungen deaktiviert"}


@router.get("/vapid-key")
async def get_vapid_key():
    """Get public VAPID key for push subscription."""
    public_key = os.getenv("VAPID_PUBLIC_KEY", "")
    return {"public_key": public_key}


@router.post("/send-test")
async def send_test_notification(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Send a test push notification to the current user."""
    user_id = current_user["id"]

    cursor = await db.execute(
        "SELECT endpoint, p256dh, auth_key FROM push_subscriptions WHERE user_id = ?",
        (user_id,),
    )
    subs = await cursor.fetchall()

    if not subs:
        raise HTTPException(status_code=404, detail="Keine Push-Subscription gefunden")

    vapid_private = os.getenv("VAPID_PRIVATE_KEY", "")
    vapid_email = os.getenv("VAPID_EMAIL", "mailto:noreply@eduai.de")

    if not vapid_private:
        return {"message": "VAPID Keys nicht konfiguriert - Test-Modus", "subscriptions": len(subs)}

    sent = 0
    for sub in subs:
        sd = dict(sub)
        try:
            from pywebpush import webpush
            webpush(
                subscription_info={
                    "endpoint": sd["endpoint"],
                    "keys": {"p256dh": sd["p256dh"], "auth": sd["auth_key"]},
                },
                data=json.dumps({
                    "title": "EduAI Test",
                    "body": "Push-Benachrichtigungen funktionieren!",
                    "icon": "/favicon.ico",
                }),
                vapid_private_key=vapid_private,
                vapid_claims={"sub": vapid_email},
            )
            sent += 1
        except Exception as e:
            logger.warning("Push notification failed: %s", e)

    return {"message": f"Test-Benachrichtigung an {sent} Geraete gesendet", "sent": sent}


@router.get("/weekly-stats")
async def get_weekly_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get weekly learning statistics (used for weekly report email)."""
    user_id = current_user["id"]

    # XP gained this week
    cursor = await db.execute(
        "SELECT xp, streak_days, quizzes_completed FROM gamification WHERE user_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    gd = dict(row) if row else {"xp": 0, "streak_days": 0, "quizzes_completed": 0}

    # Quizzes this week
    cursor = await db.execute(
        """SELECT COUNT(*) as cnt, AVG(score) as avg_score FROM quiz_results
        WHERE user_id = ? AND completed_at >= datetime('now', '-7 days')""",
        (user_id,),
    )
    row = await cursor.fetchone()
    qd = dict(row) if row else {"cnt": 0, "avg_score": 0}

    # Chats this week
    cursor = await db.execute(
        """SELECT COUNT(*) as cnt FROM activity_log
        WHERE user_id = ? AND activity_type = 'chat'
        AND created_at >= datetime('now', '-7 days')""",
        (user_id,),
    )
    row = await cursor.fetchone()
    chats = dict(row)["cnt"] if row else 0

    # Pomodoros this week
    cursor = await db.execute(
        """SELECT COUNT(*) as cnt FROM activity_log
        WHERE user_id = ? AND activity_type = 'pomodoro'
        AND created_at >= datetime('now', '-7 days')""",
        (user_id,),
    )
    row = await cursor.fetchone()
    pomodoros = dict(row)["cnt"] if row else 0

    # Strongest and weakest subjects
    cursor = await db.execute(
        """SELECT subject, AVG(score) as avg_score FROM quiz_results
        WHERE user_id = ? AND completed_at >= datetime('now', '-30 days')
        GROUP BY subject ORDER BY avg_score DESC""",
        (user_id,),
    )
    subject_rows = await cursor.fetchall()
    strongest = []
    weakest = []
    for sr in subject_rows:
        sd = dict(sr)
        entry = {"subject": sd["subject"], "avg_score": round(sd["avg_score"] or 0, 1)}
        if sd["avg_score"] and sd["avg_score"] >= 70:
            strongest.append(entry)
        else:
            weakest.append(entry)

    return {
        "total_xp": gd["xp"],
        "streak_days": gd["streak_days"],
        "week_quizzes": qd["cnt"] or 0,
        "avg_quiz_score": round(qd["avg_score"] or 0, 1),
        "week_chats": chats,
        "week_pomodoros": pomodoros,
        "week_learning_minutes": pomodoros * 25,
        "strongest_subjects": strongest[:3],
        "weakest_subjects": weakest[:3],
    }


@router.post("/send-weekly-report")
async def send_weekly_report(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Manually trigger weekly report email for current user."""
    user_id = current_user["id"]

    # Get user email
    cursor = await db.execute("SELECT email, username FROM users WHERE id = ?", (user_id,))
    user_row = await cursor.fetchone()
    if not user_row:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    ud = dict(user_row)

    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key:
        raise HTTPException(status_code=503, detail="Email-Service nicht konfiguriert")

    # Get stats
    stats_response = await get_weekly_stats(current_user=current_user, db=db)

    # Build email HTML
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; background: #f8f9fa; padding: 20px; border-radius: 12px;">
        <h1 style="color: #4f46e5;">Dein Wochen-Report</h1>
        <p>Hallo {ud['username']}! Hier ist dein Lern-Report dieser Woche:</p>

        <div style="background: white; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <h3>Statistiken</h3>
            <ul>
                <li>XP gesamt: <strong>{stats_response['total_xp']}</strong></li>
                <li>Streak: <strong>{stats_response['streak_days']} Tage</strong></li>
                <li>Quizze diese Woche: <strong>{stats_response['week_quizzes']}</strong></li>
                <li>Durchschnittsnote: <strong>{stats_response['avg_quiz_score']}%</strong></li>
                <li>Lernzeit: <strong>{stats_response['week_learning_minutes']} Min</strong></li>
                <li>Chat-Nachrichten: <strong>{stats_response['week_chats']}</strong></li>
            </ul>
        </div>

        <p style="color: #6b7280; font-size: 12px;">
            Du erhaeltst diese Email jeden Montag. | EduAI Companion
        </p>
    </div>
    """

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}"},
                json={
                    "from": "EduAI <noreply@eduai.de>",
                    "to": [ud["email"]],
                    "subject": f"Dein Wochen-Report: {stats_response['total_xp']} XP, {stats_response['week_quizzes']} Quizze",
                    "html": html,
                },
            )
            if resp.status_code not in (200, 201):
                logger.warning("Resend API error: %s %s", resp.status_code, resp.text)
                return {"message": "Email konnte nicht gesendet werden", "error": resp.text}
    except Exception as e:
        logger.error("Weekly report email failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Email fehlgeschlagen: {str(e)}")

    return {"message": f"Wochen-Report an {ud['email']} gesendet!", "stats": stats_response}


# --- Supreme 13.0 Phase 7: WebSocket real-time notifications ---
# Connection manager for active WebSocket clients
class _WSConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self):
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        if user_id not in self.active:
            self.active[user_id] = []
        self.active[user_id].append(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        if user_id in self.active:
            self.active[user_id] = [w for w in self.active[user_id] if w is not ws]
            if not self.active[user_id]:
                del self.active[user_id]

    async def send_to_user(self, user_id: int, data: dict):
        """Push a JSON message to all active sockets for a user."""
        if user_id not in self.active:
            return
        dead: list[WebSocket] = []
        for ws in self.active[user_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


ws_manager = _WSConnectionManager()


@router.websocket("/ws/{token}")
async def websocket_notifications(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time notifications (Supreme 13.0 Phase 7).

    Clients connect with their JWT token in the URL path.
    The server pushes new notifications in real-time instead of polling.
    """
    from app.core.auth import decode_token
    from jose import JWTError

    # Authenticate via token
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub", 0))
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await ws_manager.connect(user_id, websocket)
    logger.info("WebSocket connected for user %d", user_id)

    try:
        # Send initial unread count
        db_path = os.getenv("DATABASE_PATH", "app.db")
        import aiosqlite as _aiosqlite
        async with _aiosqlite.connect(db_path) as db:
            db.row_factory = _aiosqlite.Row
            cursor = await db.execute(
                "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
                (user_id,),
            )
            row = await cursor.fetchone()
            unread = dict(row)["cnt"] if row else 0
        await websocket.send_json({"type": "init", "unread_count": unread})

        # Keep connection alive; listen for client pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected for user %d", user_id)
