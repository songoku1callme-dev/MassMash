"""Quiz routes - Generate and submit quizzes with server-side answer validation.

Security: correct_answer and explanation are NEVER sent to the client during
the quiz. They are stored in the quiz_answers table and only revealed when
the student checks an individual answer or submits the entire quiz.
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.schemas import (
    QuizGenerateRequest, QuizResponse, QuizQuestionPublic,
    QuizSubmitRequest, QuizResultResponse,
    AnswerCheckRequest, AnswerCheckResponse,
)
from app.services.ai_engine import generate_quiz, update_proficiency

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz_endpoint(
    request: QuizGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Generate a quiz. Correct answers are stored server-side only."""
    user_id = current_user["id"]

    # Get current proficiency
    cursor = await db.execute(
        "SELECT proficiency_level FROM learning_profiles WHERE user_id = ? AND subject = ?",
        (user_id, request.subject)
    )
    profile = await cursor.fetchone()
    difficulty = request.difficulty
    if profile:
        level = dict(profile)["proficiency_level"]
        if request.difficulty == "auto":
            difficulty = level

    # Generate full questions (with correct_answer + explanation)
    full_questions = generate_quiz(
        subject=request.subject,
        difficulty=difficulty,
        num_questions=request.num_questions,
        quiz_type=request.quiz_type,
        language=request.language,
        topic=request.topic
    )

    quiz_id = f"quiz_{user_id}_{request.subject}_{int(datetime.now().timestamp())}"

    # Store correct answers server-side
    for q in full_questions:
        await db.execute(
            """INSERT OR REPLACE INTO quiz_answers (quiz_id, question_id, correct_answer, explanation)
            VALUES (?, ?, ?, ?)""",
            (quiz_id, q["id"], q["correct_answer"], q.get("explanation", ""))
        )
    await db.commit()

    # Build public questions (strip correct_answer and explanation)
    public_questions = [
        QuizQuestionPublic(
            id=q["id"],
            question=q["question"],
            options=q.get("options"),
            difficulty=q["difficulty"],
            topic=q.get("topic", request.subject),
        )
        for q in full_questions
    ]

    return QuizResponse(
        quiz_id=quiz_id,
        subject=request.subject,
        difficulty=difficulty,
        questions=public_questions,
    )


@router.post("/check-answer", response_model=AnswerCheckResponse)
async def check_answer(
    request: AnswerCheckRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Check a single answer against server-stored correct answer."""
    cursor = await db.execute(
        "SELECT correct_answer, explanation FROM quiz_answers WHERE quiz_id = ? AND question_id = ?",
        (request.quiz_id, request.question_id)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Quiz answer not found")

    answer_data = dict(row)
    is_correct = request.user_answer.strip().lower() == answer_data["correct_answer"].strip().lower()

    return AnswerCheckResponse(
        correct=is_correct,
        correct_answer=answer_data["correct_answer"],
        explanation=answer_data["explanation"],
    )


@router.post("/submit", response_model=QuizResultResponse)
async def submit_quiz(
    request: QuizSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Submit quiz answers. Validates against server-stored correct answers."""
    user_id = current_user["id"]

    # Fetch all correct answers for this quiz from the server
    cursor = await db.execute(
        "SELECT question_id, correct_answer FROM quiz_answers WHERE quiz_id = ?",
        (request.quiz_id,)
    )
    rows = await cursor.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Quiz not found or expired")

    correct_map = {dict(r)["question_id"]: dict(r)["correct_answer"] for r in rows}
    total = len(correct_map)

    # Score answers server-side
    correct = 0
    graded_questions = []
    for ans in request.answers:
        q_id = ans.get("question_id")
        user_answer = ans.get("user_answer", "").strip()
        server_answer = correct_map.get(q_id, "")
        is_correct = user_answer.lower() == server_answer.lower()
        if is_correct:
            correct += 1
        graded_questions.append({
            "question_id": q_id,
            "user_answer": user_answer,
            "correct_answer": server_answer,
            "is_correct": is_correct,
        })

    score = correct / total if total > 0 else 0

    # Save quiz result
    await db.execute(
        """INSERT INTO quiz_results (user_id, subject, quiz_type, total_questions, correct_answers, score, difficulty, questions)
        VALUES (?, ?, 'mcq', ?, ?, ?, ?, ?)""",
        (user_id, request.subject, total, correct, score, request.difficulty,
         json.dumps(graded_questions, ensure_ascii=False))
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

    # Clean up stored answers (quiz is done)
    await db.execute("DELETE FROM quiz_answers WHERE quiz_id = ?", (request.quiz_id,))
    await db.commit()

    # Generate feedback
    lang = current_user.get("preferred_language", "de")
    if score >= 0.8:
        feedback = "Ausgezeichnet! Du beherrschst dieses Thema sehr gut! \U0001f31f" if lang == "de" else "Excellent! You've mastered this topic! \U0001f31f"
    elif score >= 0.6:
        feedback = "Gut gemacht! Noch ein bisschen \u00dcbung und du hast es drauf! \U0001f4aa" if lang == "de" else "Good job! A bit more practice and you'll master it! \U0001f4aa"
    elif score >= 0.4:
        feedback = "Nicht schlecht, aber hier gibt es noch Verbesserungspotenzial. Lass uns die Fehler anschauen! \U0001f4da" if lang == "de" else "Not bad, but there's room for improvement. Let's review the mistakes! \U0001f4da"
    else:
        feedback = "Das Thema braucht noch etwas \u00dcbung. Keine Sorge, wir schaffen das zusammen! \U0001f91d" if lang == "de" else "This topic needs more practice. Don't worry, we'll get there together! \U0001f91d"

    return QuizResultResponse(
        total_questions=total,
        correct_answers=correct,
        score=round(score * 100, 1),
        feedback=feedback,
        new_proficiency=new_level,
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
