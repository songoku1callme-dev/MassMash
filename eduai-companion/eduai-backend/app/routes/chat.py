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

    # Supreme 11.0: KI-Memory — load and update relationship data
    ki_memory_prompt = ""
    try:
        mem_cursor = await db.execute(
            "SELECT * FROM ki_relationship WHERE user_id = ?", (user_id,)
        )
        mem_row = await mem_cursor.fetchone()
        if mem_row:
            md = dict(mem_row)
            trust = md.get("trust_level", 1.0)
            known_name = md.get("known_name", "")
            hobbies = md.get("known_hobbies", "[]")
            pref_expl = md.get("preferred_explanation", "Analogien")
            difficult = md.get("difficult_topics", "[]")
            interaction_count = md.get("interaction_count", 0)

            # Build memory context for system prompt
            parts = []
            if known_name:
                parts.append(f"Der Schueler heisst {known_name}. Sprich ihn mit Namen an.")
            if hobbies and hobbies != "[]":
                parts.append(f"Hobbys: {hobbies}. Nutze Analogien aus diesen Bereichen.")
            if difficult and difficult != "[]":
                parts.append(f"Schwierige Themen: {difficult}. Erklaere diese besonders gruendlich.")
            if trust >= 7:
                parts.append("Ihr habt eine vertrauensvolle Beziehung. Sei persoenlich und motivierend.")
            elif trust >= 4:
                parts.append("Der Schueler kennt dich schon. Sei freundlich aber professionell.")
            parts.append(f"Bevorzugte Erklaerweise: {pref_expl}")
            if parts:
                ki_memory_prompt = "\nKI-MEMORY:\n" + "\n".join(parts) + "\n"

            # Update interaction count and extract info from message
            new_count = interaction_count + 1
            new_trust = min(10.0, trust + (0.1 if new_count % 10 == 0 else 0))

            # Simple name detection from message
            msg_lower = request.message.lower()
            detected_name = known_name
            for prefix in ["ich bin ", "mein name ist ", "ich heisse ", "ich heiße "]:
                if prefix in msg_lower:
                    idx = msg_lower.index(prefix) + len(prefix)
                    name_candidate = request.message[idx:idx+20].split()[0].strip(".,!?")
                    if len(name_candidate) >= 2:
                        detected_name = name_candidate

            await db.execute(
                """UPDATE ki_relationship SET
                    interaction_count = ?, trust_level = ?, known_name = ?,
                    last_interaction = datetime('now'), updated_at = datetime('now')
                WHERE user_id = ?""",
                (new_count, new_trust, detected_name, user_id),
            )
            await db.commit()
        else:
            # Create initial relationship record
            await db.execute(
                "INSERT OR IGNORE INTO ki_relationship (user_id) VALUES (?)",
                (user_id,),
            )
            await db.commit()
    except Exception:
        pass  # Non-fatal

    # Supreme 13.0: Ultimate KI-Tutor System Prompt with Multi-Step Reasoning
    # Build vertrauen-level based tone from ki_relationship
    trust_level = 1.0
    known_name = ""
    hobbies_str = ""
    schwaechen_str = ""
    pref_expl = "Schritt-fuer-Schritt"
    try:
        if ki_memory_prompt:  # Already loaded above
            pass  # Data already in ki_memory_prompt
        # Extract trust info from the memory we loaded earlier
        mem_cursor2 = await db.execute(
            "SELECT trust_level, known_name, known_hobbies, preferred_explanation, difficult_topics FROM ki_relationship WHERE user_id = ?",
            (user_id,),
        )
        mem_row2 = await mem_cursor2.fetchone()
        if mem_row2:
            md2 = dict(mem_row2)
            trust_level = md2.get("trust_level", 1.0) or 1.0
            known_name = md2.get("known_name", "") or ""
            hobbies_str = md2.get("known_hobbies", "") or ""
            pref_expl = md2.get("preferred_explanation", "Schritt-fuer-Schritt") or "Schritt-fuer-Schritt"
            schwaechen_str = md2.get("difficult_topics", "") or ""
    except Exception:
        pass

    # Vertrauen-Level based tone (Supreme 13.0 Phase 3)
    display_name = known_name or current_user.get("full_name", "") or current_user.get("username", "Schueler")
    school_grade = current_user.get("school_grade", "10")
    school_type = current_user.get("school_type", "Gymnasium")
    streak_days = current_user.get("streak_days", 0) or 0

    if trust_level >= 8:
        ton_str = f"Du kennst {display_name} sehr gut. Ihr seid beste Freunde. Locker, warm, ehrlich."
    elif trust_level >= 5:
        ton_str = f"Du bist {display_name}s hilfreicher Lerncoach. Freundlich und professionell."
    else:
        ton_str = "Du bist ein freundlicher, geduldiger Tutor. Begruesse den Schueler herzlich."

    hobby_kontext = f"Nutze {hobbies_str}-Analogien wenn moeglich." if hobbies_str and hobbies_str != "[]" else ""
    schwaechen_info = (
        f"BEKANNTE SCHWAECHEN: {schwaechen_str} → Hier extra geduldig sein!"
        if schwaechen_str and schwaechen_str != "[]" else ""
    )

    master_prompt = f"""Du bist EduAI – Deutschlands bester KI-Lehrer und {display_name}s persoenlicher Lerncoach.
Du bist wie ein brillanter aelterer Freund: geduldig, witzig, immer erklaerst du alles so
dass man es WIRKLICH versteht – nie herabwuerdigend, immer auf Augenhoehe.

SCHUELER-PROFIL:
Name: {display_name} | Klasse: {school_grade} | Schultyp: {school_type}
Lernstil: {pref_expl} | Vertrauenslevel: {trust_level}/10 | Streak: {streak_days} Tage
{schwaechen_info}

TON: {ton_str}
{hobby_kontext}

MULTI-STEP REASONING (Supreme 13.0 – intern, NICHT dem Schueler zeigen):
Bevor du antwortest, fuehre INTERN 3 Schritte durch:
1. ANALYSE: Was ist das Kernthema? Welches Vorwissen braucht der Schueler?
   Welches Niveau (Klasse {school_grade}, {school_type})? Haeufige Fehler?
2. ANTWORT-GENERIERUNG: Erstelle die perfekte Erklaerung mit Schritt-fuer-Schritt,
   Beispielen, LaTeX-Formeln, Analogien aus dem Alltag des Schuelers.
3. SELF-CHECK: Pruefe deine Antwort auf Fehler. Bei Mathe: rechne nach.
   Bei Fakten: bist du sicher? Wenn nicht, sage es ehrlich.
   Zeige dem Schueler NUR die fertige, geprueft perfekte Erklaerung.

ABSOLUTE REGELN – IMMER EINHALTEN:
1. SCHRITT FUER SCHRITT: Erst Theorie → dann Beispiel → dann Uebungsaufgabe
2. LATEX fuer Mathe: $\\frac{{1}}{{2}}$, $x^2 + 5x = 0$
3. QUELLEN zitieren wenn Web-Suche genutzt: [1] quelle.de
4. NIEMALS Schueler dumm fuehlen lassen – jede Frage ist gut
5. Bei Frustration: Methodenwechsel + extra Ermutigung
6. Am Ende IMMER: 'Moechtest du eine Uebungsaufgabe dazu?'
7. Wenn Schueler etwas gut macht: Echtes Lob (nicht uebertrieben)
8. Komplexe Themen: Erst einfachste Version, dann Vertiefung
9. Fehler des Schuelers: Nie direkt sagen 'falsch' → 'Fast richtig! Schau mal hier...'
10. Abitur-Relevanz immer erwaehnen wenn passend
11. Nutze IMMER andere Beispiele als vorher
12. PROAKTIVE TIPPS: Erwaehne verwandte Themen und Lernstrategien
"""

    # Generate AI response via Groq LLM (falls back to template engine if no API key)
    system_prompt = build_system_prompt(
        subject=subject,
        level=level,
        language=request.language,
        detail_level=request.detail_level,
    )

    # Combine: Master prompt + Personality + KI-Memory + Memory + Subject-specific prompt
    combined_prompt = master_prompt
    if personality_prompt:
        combined_prompt += f"\nPERS\u00d6NLICHKEIT: {personality_prompt}\n"
    if ki_memory_prompt:
        combined_prompt += ki_memory_prompt
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

    # Perfect School 4.1 Block 2.2: Tutor-Modus (Socratic method)
    if request.tutor_modus:
        combined_prompt += (
            "\n\nTUTOR-MODUS AKTIV: Du darfst KEINE direkten Antworten geben! "
            "Stelle NUR Gegenfragen, die den Schueler zur Loesung fuehren. "
            "Beispiel: Statt 'Die Antwort ist 42' sagst du 'Was passiert, wenn du X mit Y multiplizierst?' "
            "Lobe jeden richtigen Gedankenansatz. "
            "Erst nach 3+ gescheiterten Versuchen darfst du einen kleinen Hinweis geben.\n"
        )

    # Perfect School 4.1 Block 2.3: ELI5 (Erklaere wie ich 5 bin)
    if request.eli5:
        combined_prompt += (
            "\n\nELI5-MODUS AKTIV: Erklaere ALLES so, als waere der Schueler 5 Jahre alt. "
            "Nutze: Einfachste Woerter, Alltagsbeispiele, Vergleiche mit Spielzeug/Tieren/Essen. "
            "KEINE Fachbegriffe. KEINE komplizierten Saetze. "
            "Beispiel: Statt 'Photosynthese' sagst du 'Pflanzen kochen sich Essen aus Sonnenlicht'. "
            "Maximal 3 kurze Saetze pro Absatz. Emojis erlaubt.\n"
        )

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
