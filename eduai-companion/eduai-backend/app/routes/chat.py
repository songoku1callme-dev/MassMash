"""Chat routes - AI-powered tutoring conversations."""
import json
import logging
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.schemas import ChatRequest, ChatResponse, ChatSessionResponse
from app.services.ai_engine import detect_subject, build_system_prompt
from app.services.groq_llm import call_groq_llm, classify_needs_search
from app.services import rag_service
from app.services.ki_personalities import get_personality_by_id, is_personality_accessible
from app.services.ki_intelligence import detect_lernstil, get_lernstil_prompt, detect_emotion, get_emotion_prompt

logger = logging.getLogger(__name__)

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

    # Check user subscription tier and personality
    cursor = await db.execute(
        "SELECT is_pro, subscription_tier, ki_personality_id FROM users WHERE id = ?",
        (user_id,),
    )
    pro_row = await cursor.fetchone()
    pro_dict = dict(pro_row) if pro_row else {}
    is_pro = bool(pro_dict.get("is_pro", 0))
    user_tier = pro_dict.get("subscription_tier", "free") or "free"

    # Determine personality to use (from request or user profile)
    personality_id = request.personality_id or pro_dict.get("ki_personality_id", 1) or 1
    personality = get_personality_by_id(personality_id)
    personality_prompt = ""
    personality_temperature = None
    if personality and is_personality_accessible(personality_id, user_tier):
        personality_prompt = personality["system_prompt"]
        personality_temperature = personality["temperature"]

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

    # Search RAG index for relevant curriculum context
    rag_context = ""
    rag_sources: list[str] = []
    try:
        rag_results = await rag_service.search_similar(
            query=request.message,
            top_k=3,
            filter_metadata={"subject": subject} if subject != "general" else None,
        )
        if rag_results:
            context_parts = []
            for r in rag_results:
                context_parts.append(r["chunk_text"])
                source = r.get("source", r["doc_id"])
                if source not in rag_sources:
                    rag_sources.append(source)
            rag_context = "\n---\n".join(context_parts)
    except Exception as rag_err:
        logger.warning("RAG search failed (non-fatal): %s", rag_err)

    # Fetch adaptive memory prompt for weak topics
    memory_hint = ""
    try:
        mem_cursor = await db.execute(
            """SELECT topic_name, feedback_score FROM user_memories
            WHERE user_id = ? AND subject = ? AND schwach = 1
            ORDER BY feedback_score ASC LIMIT 5""",
            (user_id, subject),
        )
        mem_rows = await mem_cursor.fetchall()
        if mem_rows:
            weak_names = [dict(r)["topic_name"] for r in mem_rows if dict(r)["topic_name"]]
            if weak_names:
                memory_hint = (
                    f"\nERINNERUNG: Der Sch\u00fcler hat Schwierigkeiten mit: {', '.join(weak_names)}. "
                    "Erkl\u00e4re diese Themen besonders gr\u00fcndlich und gib zus\u00e4tzliche Beispiele.\n"
                )
    except Exception:
        pass  # Non-fatal

    # Auto-Web-Search for Pro/Max users (Phase 2.1)
    web_context = ""
    web_sources: list[str] = []
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if tavily_key and user_tier in ("pro", "max") and classify_needs_search(request.message):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                search_query = f"{request.message} Deutschland Gymnasium Lehrplan"
                resp = await http_client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": search_query,
                        "search_depth": "basic",
                        "max_results": 3,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for idx, r in enumerate(data.get("results", [])[:3], 1):
                        web_context += f"[{idx}] {r.get('title', '')}: {r.get('content', '')[:300]}\n"
                        web_sources.append(f"[{idx}] [{r.get('title', '')}]({r.get('url', '')})")
        except Exception as web_err:
            logger.warning("Auto web search failed (non-fatal): %s", web_err)

    # Master KI-Tutor System Prompt
    master_prompt = (
        "Du bist EduAI, der intelligenteste KI-Tutor Deutschlands. "
        "Du unterrichtest Schueler der Klassen 5-13 auf Abitur-Niveau.\n"
        "REGELN:\n"
        "1. Erklaere Schritt fuer Schritt mit konkreten Beispielen\n"
        "2. Verwende LaTeX fuer Mathematik: $F = m \\cdot a$\n"
        "3. Strukturiere Antworten mit Ueberschriften und Aufzaehlungen\n"
        "4. Gib am Ende immer 1-2 Uebungsaufgaben\n"
        "5. Passe dich dem Niveau des Schuelers an\n"
        "6. Sei motivierend und ermutigend\n"
        "7. Wenn du Quellen hast, zitiere sie\n"
        "8. Ende immer mit: 'Moechtest du eine Uebungsaufgabe dazu?'\n"
    )

    # Generate AI response via Groq LLM (falls back to template engine if no API key)
    system_prompt = build_system_prompt(
        subject=subject,
        level=level,
        language=request.language,
        detail_level=request.detail_level,
    )

    # Combine: Master prompt + Personality + Memory + Subject-specific prompt
    combined_prompt = master_prompt
    if personality_prompt:
        combined_prompt += f"\nPERS\u00d6NLICHKEIT: {personality_prompt}\n"
    if memory_hint:
        combined_prompt += memory_hint
    combined_prompt += f"\n{system_prompt}"

    # Phase 3 Supreme 9.0: Lernstil-Erkennung + Emotionale Intelligenz
    # Detect emotion from current message
    emotion = detect_emotion(request.message)
    emotion_prompt = get_emotion_prompt(emotion)
    if emotion_prompt:
        combined_prompt += f"\n{emotion_prompt}"

    # Detect learning style from chat history (after 5+ messages)
    if len(messages) >= 5:
        try:
            lernstil = await detect_lernstil(messages)
            lernstil_prompt = get_lernstil_prompt(lernstil)
            if lernstil_prompt:
                combined_prompt += lernstil_prompt
        except Exception:
            pass  # Non-fatal

    # Detect "explain differently" requests (Phase 2.5)
    explain_methods = [
        ("verstehe ich nicht", "Erklaere es anders, mit einer Analogie. Beginne mit 'Stell dir vor...'"),
        ("zu kompliziert", "Erklaere es viel einfacher, als wuerdest du es einem Freund erklaeren."),
        ("noch mal", "Erklaere es visuell mit Schritt-fuer-Schritt Auflistung und Beispielen."),
        ("anders erklaeren", "Nutze eine komplett andere Erklaermethode als vorher."),
    ]
    msg_lower = request.message.lower()
    for trigger, extra_instruction in explain_methods:
        if trigger in msg_lower:
            combined_prompt += f"\nWICHTIG: {extra_instruction}\n"
            break

    ai_response = call_groq_llm(
        prompt=request.message,
        system_prompt=combined_prompt,
        subject=subject,
        level=level,
        language=request.language,
        chat_history=messages,
        rag_context=rag_context,
        is_pro=is_pro,
        temperature_override=personality_temperature,
        web_context=web_context,
    )

    # Award gamification XP for chat
    try:
        from app.routes.gamification import add_xp
        await add_xp(user_id, 5, "chat", db)
    except Exception:
        pass  # Non-fatal

    # Append source references if RAG or web search provided context
    all_sources = []
    if rag_sources and rag_context:
        all_sources.extend([f"- {s}" for s in rag_sources])
    if web_sources:
        all_sources.extend(web_sources)
    if all_sources:
        sources_text = "\n".join(all_sources)
        if request.language == "de":
            ai_response += f"\n\n---\n**Quellen:**\n{sources_text}"
        else:
            ai_response += f"\n\n---\n**Sources:**\n{sources_text}"

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


@router.post("/feedback")
async def chat_feedback(
    message_index: int,
    session_id: int,
    rating: str,
    reason: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit feedback on a KI response (Phase 2.2 Feedback Loop).

    rating: 'positive' or 'negative'
    reason: optional text (zu kompliziert / falsch / zu kurz / sonstiges)
    """
    user_id = current_user["id"]

    # Store feedback
    await db.execute(
        """INSERT INTO chat_feedback (user_id, session_id, message_index, rating, reason)
        VALUES (?, ?, ?, ?, ?)""",
        (user_id, session_id, message_index, rating, reason),
    )
    await db.commit()

    return {"message": "Feedback gespeichert", "rating": rating}


@router.get("/feedback-stats")
async def feedback_stats(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get feedback statistics (admin only)."""
    cursor = await db.execute(
        "SELECT rating, COUNT(*) as cnt FROM chat_feedback GROUP BY rating"
    )
    rows = await cursor.fetchall()
    stats = {dict(r)["rating"]: dict(r)["cnt"] for r in rows}
    total = sum(stats.values())
    positive = stats.get("positive", 0)
    rate = round(positive / total * 100, 1) if total > 0 else 0
    return {"total": total, "positive": positive, "negative": stats.get("negative", 0), "positive_rate": rate}
