"""Quiz routes - Generate and submit quizzes."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.schemas import (
    QuizGenerateRequest, QuizResponse, QuizSubmitRequest, QuizResultResponse
)
from app.services.ai_engine import generate_quiz, update_proficiency

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz_endpoint(
    request: QuizGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Generate a quiz for a subject."""
    user_id = current_user["id"]

    # Get current proficiency
    cursor = await db.execute(
        "SELECT proficiency_level FROM learning_profiles WHERE user_id = ? AND subject = ?",
        (user_id, request.subject)
    )
    profile = await cursor.fetchone()
    difficulty = request.difficulty
    if profile:
        # Use proficiency to suggest difficulty if not specified
        level = dict(profile)["proficiency_level"]
        if request.difficulty == "auto":
            difficulty = level

    questions = generate_quiz(
        subject=request.subject,
        difficulty=difficulty,
        num_questions=request.num_questions,
        quiz_type=request.quiz_type,
        language=request.language,
        topic=request.topic
    )

    quiz_id = f"quiz_{user_id}_{request.subject}_{int(datetime.now().timestamp())}"

    return QuizResponse(
        quiz_id=quiz_id,
        subject=request.subject,
        difficulty=difficulty,
        questions=questions
    )


@router.post("/submit", response_model=QuizResultResponse)
async def submit_quiz(
    request: QuizSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Submit quiz answers and get results."""
    user_id = current_user["id"]
    total = len(request.questions)
    correct = sum(
        1 for q in request.questions
        if q.get("user_answer", "").strip().lower() == q.get("correct_answer", "").strip().lower()
    )
    score = correct / total if total > 0 else 0

    # Save quiz result
    await db.execute(
        """INSERT INTO quiz_results (user_id, subject, quiz_type, total_questions, correct_answers, score, difficulty, questions)
        VALUES (?, ?, 'mcq', ?, ?, ?, ?, ?)""",
        (user_id, request.subject, total, correct, score, request.difficulty,
         json.dumps(request.questions, ensure_ascii=False))
    )
    await db.commit()

    # Update learning profile
    cursor = await db.execute(
        "SELECT * FROM learning_profiles WHERE user_id = ? AND subject = ?",
        (user_id, request.subject)
    )
    profile = await cursor.fetchone()
    if profile:
        profile_dict = dict(profile)
        new_total = profile_dict["total_questions_answered"] + total
        new_correct = profile_dict["correct_answers"] + correct
        new_mastery = new_correct / new_total if new_total > 0 else 0
        new_level = update_proficiency(profile_dict["proficiency_level"], correct, total)

        await db.execute(
            """UPDATE learning_profiles SET
                total_questions_answered = ?,
                correct_answers = ?,
                mastery_score = ?,
                proficiency_level = ?,
                last_active = datetime('now')
            WHERE user_id = ? AND subject = ?""",
            (new_total, new_correct, new_mastery, new_level, user_id, request.subject)
        )
        await db.commit()
    else:
        new_level = "beginner"

    # Log activity
    await db.execute(
        """INSERT INTO activity_log (user_id, activity_type, subject, description, metadata)
        VALUES (?, 'quiz', ?, ?, ?)""",
        (user_id, request.subject, f"Completed quiz: {correct}/{total}",
         json.dumps({"score": score, "correct": correct, "total": total}))
    )
    await db.commit()

    # Generate feedback
    if score >= 0.8:
        feedback = "Ausgezeichnet! Du beherrschst dieses Thema sehr gut! 🌟" if current_user.get("preferred_language", "de") == "de" else "Excellent! You've mastered this topic! 🌟"
    elif score >= 0.6:
        feedback = "Gut gemacht! Noch ein bisschen Übung und du hast es drauf! 💪" if current_user.get("preferred_language", "de") == "de" else "Good job! A bit more practice and you'll master it! 💪"
    elif score >= 0.4:
        feedback = "Nicht schlecht, aber hier gibt es noch Verbesserungspotenzial. Lass uns die Fehler anschauen! 📚" if current_user.get("preferred_language", "de") == "de" else "Not bad, but there's room for improvement. Let's review the mistakes! 📚"
    else:
        feedback = "Das Thema braucht noch etwas Übung. Keine Sorge, wir schaffen das zusammen! 🤝" if current_user.get("preferred_language", "de") == "de" else "This topic needs more practice. Don't worry, we'll get there together! 🤝"

    return QuizResultResponse(
        total_questions=total,
        correct_answers=correct,
        score=round(score * 100, 1),
        feedback=feedback,
        new_proficiency=new_level
    )


@router.get("/history")
async def quiz_history(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Get quiz history for current user."""
    cursor = await db.execute(
        """SELECT id, subject, quiz_type, total_questions, correct_answers, score, difficulty, completed_at
        FROM quiz_results WHERE user_id = ? ORDER BY completed_at DESC LIMIT 20""",
        (current_user["id"],)
    )
    results = await cursor.fetchall()
    return [dict(r) for r in results]
