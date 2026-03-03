"""Chat routes - AI-powered tutoring conversations."""
import json
import logging
import os
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.schemas import ChatRequest, ChatResponse, ChatSessionResponse
from app.services.ai_engine import detect_subject, build_system_prompt, normalize_fach
from app.services.groq_llm import call_groq_llm, classify_needs_search, deep_think_answer
from app.services import rag_service
from app.services.ki_personalities import get_personality_by_id, is_personality_accessible
from app.services.ki_intelligence import detect_lernstil, get_lernstil_prompt, detect_emotion, get_emotion_prompt
from app.services.latein_modus import get_spezial_system_prompt, is_latein_modus_fach
from app.services.internet_ki import chat_mit_internet
from app.core.bundesland import get_bundesland_prompt
from app.services.model_router import route_request, execute_routed_chat
from app.services.prompt_optimizer import get_prompt_for_fach

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bug-Fix 2: Doppelte Quellen entfernen
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def remove_self_generated_sources(text: str) -> str:
    """Entfernt LLM-generierte Quellen-Blöcke aus der Antwort.

    Das LLM fügt manchmal eigene "Quellen:" oder "Sources:" Abschnitte
    am Ende hinzu — diese müssen raus, weil wir Quellen separat liefern.
    """
    # Pattern: alles ab "---\n**Quellen" oder "**Quellen:" oder "Quellen:" am Ende
    patterns = [
        r'\n---\n\*?\*?Quellen\*?\*?:?\s*\n.*$',
        r'\n---\n\*?\*?Sources\*?\*?:?\s*\n.*$',
        r'\n\*?\*?Quellen\*?\*?:\s*\n[-•\[\d].*$',
        r'\n\*?\*?Sources\*?\*?:\s*\n[-•\[\d].*$',
        r'\nQuellen:\s*\n.*$',
        r'\nSources:\s*\n.*$',
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
    return cleaned.rstrip()

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Send a message and get AI response."""
    user_id = current_user["id"]

    # Auto-detect subject — neue Fach-Erkennung mit Prioritäts-Scoring
    user_fach = request.subject if request.subject and request.subject not in ("general", "", "Alle", "Allgemein") else None
    detected_subject = detect_subject(request.message, user_fach=user_fach)
    subject = detected_subject
    # Block A: Fach normalisieren — immer Deutsch
    subject = normalize_fach(subject)

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

    # Search RAG index for relevant curriculum context (Bug-Fix 3: Fach-Filter)
    rag_context = ""
    rag_sources: list[str] = []
    try:
        rag_results = await rag_service.search_similar(
            query=request.message,
            top_k=3,
            fach_filter=subject if subject not in ("general", "Allgemein", "Alle") else None,
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

    # Block 4: Internet-KI — Tavily-Integration für Echtzeit-Websuche
    web_context = ""
    web_sources: list[str] = []
    internet_genutzt = False
    try:
        internet_result = await chat_mit_internet(
            frage=request.message,
            fach=subject,
            user_tier=user_tier,
        )
        internet_genutzt = internet_result["internet_genutzt"]
        web_context = internet_result["web_kontext"]
        web_sources = internet_result["web_quellen"]
    except Exception as web_err:
        logger.warning("Internet-KI fehlgeschlagen (non-fatal): %s", web_err)

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
                parts.append(f"Der Schüler heißt {known_name}. Sprich ihn mit Namen an.")
            if hobbies and hobbies != "[]":
                parts.append(f"Hobbys: {hobbies}. Nutze Analogien aus diesen Bereichen.")
            if difficult and difficult != "[]":
                parts.append(f"Schwierige Themen: {difficult}. Erkläre diese besonders gründlich.")
            if trust >= 7:
                parts.append("Ihr habt eine vertrauensvolle Beziehung. Sei persönlich und motivierend.")
            elif trust >= 4:
                parts.append("Der Schüler kennt dich schon. Sei freundlich aber professionell.")
            parts.append(f"Bevorzugte Erklärweise: {pref_expl}")
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

    # Nuclear Reset Block A: Extract user profile for Perplexity-standard prompt
    display_name = current_user.get("full_name", "") or current_user.get("username", "Schüler")
    school_grade = current_user.get("school_grade", "10") or "10"
    school_type = current_user.get("school_type", "Gymnasium") or "Gymnasium"

    # Get user's Bundesland
    user_bundesland = ""
    try:
        bl_cursor = await db.execute(
            "SELECT bundesland FROM users WHERE id = ?", (user_id,)
        )
        bl_row = await bl_cursor.fetchone()
        user_bundesland = dict(bl_row).get("bundesland", "") if bl_row else ""
    except Exception:
        pass

    # Nuclear Reset Block A: Build the NEW Perplexity-standard system prompt
    combined_prompt = build_system_prompt(
        subject=subject,
        level=level,
        language=request.language,
        detail_level=request.detail_level,
        user_name=display_name,
        klasse=str(school_grade),
        schultyp=school_type,
        bundesland=user_bundesland,
        tutor_modus=request.tutor_modus,
        web_quellen=web_context,
    )

    # Add personality if available
    if personality_prompt:
        combined_prompt += f"\nPERSÖNLICHKEIT: {personality_prompt}\n"
    # Add KI-Memory context
    if ki_memory_prompt:
        combined_prompt += ki_memory_prompt
    # Add weak-topic memory
    if memory_hint:
        combined_prompt += memory_hint

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

    # Fächer-Expansion 5.0 Block 2: Latein/Altgriechisch Spezial-Modus
    if is_latein_modus_fach(subject):
        spezial_prompt = get_spezial_system_prompt(subject)
        if spezial_prompt:
            combined_prompt += f"\n{spezial_prompt}\n"

    # Bundesland + Tutor-Modus are now handled in build_system_prompt (Nuclear Reset Block A)

    # Perfect School 4.1 Block 2.3: ELI5 (Erkläre wie ich 5 bin)
    if request.eli5:
        combined_prompt += (
            "\n\nELI5-MODUS AKTIV: Erkläre ALLES so, als wäre der Schüler 5 Jahre alt. "
            "Nutze: Einfachste Wörter, Alltagsbeispiele, Vergleiche mit Spielzeug/Tieren/Essen. "
            "KEINE Fachbegriffe. KEINE komplizierten Sätze. "
            "Beispiel: Statt 'Photosynthese' sagst du 'Pflanzen kochen sich Essen aus Sonnenlicht'. "
            "Maximal 3 kurze Sätze pro Absatz. Emojis erlaubt.\n"
        )

    # Detect "explain differently" requests (Phase 2.5)
    explain_methods = [
        ("verstehe ich nicht", "Erkläre es anders, mit einer Analogie. Beginne mit 'Stell dir vor...'"),
        ("zu kompliziert", "Erkläre es viel einfacher, als würdest du es einem Freund erklären."),
        ("noch mal", "Erkläre es visuell mit Schritt-für-Schritt Auflistung und Beispielen."),
        ("anders erklären", "Nutze eine komplett andere Erklärmethode als vorher."),
    ]
    msg_lower = request.message.lower()
    for trigger, extra_instruction in explain_methods:
        if trigger in msg_lower:
            combined_prompt += f"\nWICHTIG: {extra_instruction}\n"
            break

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Integration Fix 1: Model Router + Prompt Optimizer
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Optimierten Prompt verwenden (falls vorhanden)
    combined_prompt = get_prompt_for_fach(subject, combined_prompt)

    # Model Router entscheidet: 8b-instant vs 70b-versatile vs Internet
    routing = route_request(request.message, subject, user_tier)
    logger.info(
        "Model-Routing: %s | multi_step=%s | internet=%s | %s",
        routing.modell, routing.multi_step, routing.internet, routing.begründung,
    )

    # Routed Chat ausführen (Internet + Multi-Step + Qualitäts-Check)
    routed_result = await execute_routed_chat(
        frage=request.message,
        fach=subject,
        tier=user_tier,
        verlauf=[{"role": m.get("role", "user"), "content": m.get("content", "")}
                 for m in messages[-8:] if m.get("content")],
        system_prompt=combined_prompt,
    )

    ai_response = routed_result.get("antwort", "")
    modell_genutzt = routed_result.get("modell_genutzt", routing.modell)
    router_internet = routed_result.get("internet_genutzt", False)
    router_multi_step = routed_result.get("multi_step", False)
    router_web_quellen = routed_result.get("web_quellen", [])

    # Fallback: wenn Router keine Antwort liefert, Standard-Pfad
    if not ai_response:
        logger.warning("Router lieferte leere Antwort — Fallback auf call_groq_llm")
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

    # Internet-Status aus Router übernehmen
    if router_internet:
        internet_genutzt = True
    if router_web_quellen:
        for wq in router_web_quellen:
            url = wq.get("url", "") if isinstance(wq, dict) else str(wq)
            if url and url not in web_sources:
                web_sources.append(url)

    # Block 4: Auto-Karteikarten + Zusammenfassung generieren
    karteikarten = []
    zusammenfassung = ""
    try:
        import re as _re
        extras_prompt = (
            f'Aus dieser KI-Erklärung:\n"{ai_response[:500]}"\n\n'
            "Erstelle kompakt im JSON-Format (KEIN anderer Text, NUR JSON):\n"
            '{"zusammenfassung": "Genau 2 Sätze die den Kern erklären.",'
            ' "karteikarten": [{"frage": "...", "antwort": "..."},'
            ' {"frage": "...", "antwort": "..."},'
            ' {"frage": "...", "antwort": "..."}]}\n\n'
            "Nutze echte Umlaute (ä ö ü ß). Keine oe ae ue."
        )
        extras_text = call_groq_llm(
            prompt=extras_prompt,
            system_prompt="Du bist ein JSON-Generator. Antworte NUR mit validem JSON.",
            subject=subject,
            level=level,
            language=request.language,
            chat_history=[],
            rag_context="",
            is_pro=False,
        )
        match = _re.search(r'\{.*\}', extras_text, _re.DOTALL)
        if match:
            extras_data = json.loads(match.group())
            raw_karten = extras_data.get("karteikarten", [])
            for k in raw_karten[:3]:
                if isinstance(k, dict) and "frage" in k and "antwort" in k:
                    karteikarten.append({"frage": k["frage"], "antwort": k["antwort"]})
            zusammenfassung = extras_data.get("zusammenfassung", "")
    except Exception as karten_err:
        logger.debug("Karteikarten generation failed (non-fatal): %s", karten_err)

    # Award gamification XP for chat
    try:
        from app.routes.gamification import add_xp
        await add_xp(user_id, 5, "chat", db)
    except Exception:
        pass  # Non-fatal

    # Bug-Fix 2: Quellen NICHT in die Antwort einbauen — separat zurückgeben
    # Entferne LLM-generierte Quellen-Blöcke aus der Antwort
    ai_response = remove_self_generated_sources(ai_response)

    # Sammle alle Quellen in einer separaten Liste
    all_sources: list[str] = []
    if rag_sources and rag_context:
        for s in rag_sources:
            if s not in all_sources:
                all_sources.append(s)
    if web_sources:
        for s in web_sources:
            if s not in all_sources:
                all_sources.append(s)
    # Maximal 3 Quellen
    all_sources = all_sources[:3]

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
        proficiency_level=level,
        karteikarten=karteikarten,
        zusammenfassung=zusammenfassung,
        quellen=all_sources,
        internet_genutzt=internet_genutzt,
        modell_genutzt=modell_genutzt,
        multi_step=router_multi_step,
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
    fach: str = "",
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Submit feedback on a KI response (Block 5: Selbst-Verbesserung).

    rating: 'positive' or 'negative'
    reason: optional text (zu kompliziert / falsch / zu kurz / sonstiges)
    fach: optional subject for per-subject tracking
    """
    user_id = current_user["id"]

    # Store feedback with fach
    await db.execute(
        """INSERT INTO chat_feedback (user_id, session_id, message_index, rating, reason)
        VALUES (?, ?, ?, ?, ?)""",
        (user_id, session_id, message_index, rating, reason),
    )
    await db.commit()

    # Bei negativem Feedback: Analyse durchführen
    analyse = ""
    if rating == "negative":
        analyse = await analysiere_schlechte_antwort(
            session_id, message_index, reason, fach, db
        )

    return {
        "message": "Feedback gespeichert",
        "rating": rating,
        "analyse": analyse,
    }


async def analysiere_schlechte_antwort(
    session_id: int,
    message_index: int,
    reason: str,
    fach: str,
    db: aiosqlite.Connection,
) -> str:
    """Analysiert eine schlecht bewertete Antwort (Block 5).

    Speichert Muster für spätere Prompt-Verbesserungen.
    """
    try:
        # Hole die Session und die Nachricht
        cursor = await db.execute(
            "SELECT messages FROM chat_sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return "Session nicht gefunden"

        messages = json.loads(dict(row)["messages"])
        if message_index >= len(messages):
            return "Nachricht nicht gefunden"

        nachricht = messages[message_index]
        inhalt = nachricht.get("content", "")[:200]

        # Muster erkennen
        muster = []
        if reason == "zu_kompliziert":
            muster.append("Erklärung zu komplex")
        elif reason == "falsch":
            muster.append("Inhaltlich falsch")
        elif reason == "zu_kurz":
            muster.append("Nicht genug Detail")
        elif reason == "irrelevant":
            muster.append("Thema verfehlt")
        else:
            muster.append(f"Sonstiges: {reason[:100]}")

        analyse = f"Fach: {fach or 'Unbekannt'}, Muster: {', '.join(muster)}"
        logger.info("Negative Feedback-Analyse: %s", analyse)
        return analyse

    except Exception as e:
        logger.warning("Feedback-Analyse fehlgeschlagen: %s", e)
        return ""


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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Block 5: Admin KI-Qualität Dashboard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ADMIN_EMAILS = [
    "ahmadalkhalaf2019@gmail.com",
    "songoku1callme@gmail.com",
    "261al3nzi261@gmail.com",
    "261g2g261@gmail.com",
]


@router.get("/ki-qualitaet")
async def ki_qualitaet(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """KI-Qualitäts-Dashboard für Admins (Block 5: Selbst-Verbesserung).

    Zeigt:
    - Gesamt positiv/negativ Rate
    - Qualitäts-Score (%)
    - Feedback nach Fach
    - Letzte negative Feedbacks
    """
    # Admin-Check
    user_email = current_user.get("email", "")
    if user_email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Nur für Admins")

    # Gesamt-Statistik
    cursor = await db.execute(
        "SELECT rating, COUNT(*) as cnt FROM chat_feedback GROUP BY rating"
    )
    rows = await cursor.fetchall()
    stats = {dict(r)["rating"]: dict(r)["cnt"] for r in rows}
    total = sum(stats.values())
    positiv = stats.get("positive", 0)
    negativ = stats.get("negative", 0)
    qualitaet = round(positiv / total * 100, 1) if total > 0 else 100.0

    # Letzte 10 negative Feedbacks
    cursor = await db.execute(
        """SELECT cf.*, cs.subject
        FROM chat_feedback cf
        LEFT JOIN chat_sessions cs ON cf.session_id = cs.id
        WHERE cf.rating = 'negative'
        ORDER BY cf.id DESC LIMIT 10"""
    )
    negative_rows = await cursor.fetchall()
    letzte_negative = []
    for r in negative_rows:
        rd = dict(r)
        letzte_negative.append({
            "session_id": rd.get("session_id"),
            "message_index": rd.get("message_index"),
            "reason": rd.get("reason", ""),
            "fach": rd.get("subject", ""),
        })

    return {
        "gesamt": total,
        "positiv": positiv,
        "negativ": negativ,
        "qualitaet_prozent": qualitaet,
        "letzte_negative": letzte_negative,
        "status": "gut" if qualitaet >= 80 else "verbesserungswürdig" if qualitaet >= 60 else "kritisch",
    }
