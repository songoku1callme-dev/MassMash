"""OCR + Math Solver endpoints with intelligent classification.

Supreme 9.0 Phase 7: Foto-Solver Upgrade - OCR + Klassifizierung + intelligentes Routing.
"""
import os
import logging
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from app.core.auth import get_current_user
from app.services.ocr_solver import MathSolver
from app.services.groq_llm import call_groq_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

SUBJECT_CLASSIFICATION = {
    "mathe": "math", "mathematik": "math", "math": "math",
    "physik": "physics", "physics": "physics",
    "chemie": "chemistry", "chemistry": "chemistry",
    "biologie": "biology", "biology": "biology",
    "deutsch": "german", "german": "german",
    "englisch": "english", "english": "english",
    "geschichte": "history", "history": "history",
    "text": "text",
}


def classify_image_content(ocr_text: str) -> str:
    """Classify OCR text into subject category."""
    text_lower = ocr_text.lower()
    # Math indicators
    math_indicators = ["=", "+", "-", "*", "/", "x", "^", "integral", "ableitung", "gleichung", "formel"]
    physics_indicators = ["kraft", "energie", "geschwindigkeit", "beschleunigung", "newton", "joule", "watt", "volt"]
    chemistry_indicators = ["mol", "reaktion", "element", "atom", "molekuel", "saeure", "base", "ph"]
    biology_indicators = ["zelle", "dna", "protein", "evolution", "oekosystem", "photosynthese"]

    scores = {
        "math": sum(1 for i in math_indicators if i in text_lower),
        "physics": sum(1 for i in physics_indicators if i in text_lower),
        "chemistry": sum(1 for i in chemistry_indicators if i in text_lower),
        "biology": sum(1 for i in biology_indicators if i in text_lower),
    }
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] == 0:
        return "text"
    return best


@router.post("/solve-image")
async def solve_from_image(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
) -> dict:
    """Upload an image → OCR → Classify → Route to correct solver.

    Supreme 9.0: Intelligent classification + routing.
    - Math: SymPy solver with step-by-step
    - Physics/Chemistry/Biology: Groq LLM with subject-specific prompts
    - Text: Groq LLM general explanation
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Nur Bilddateien erlaubt (JPEG, PNG, etc.)")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="Datei zu gross (max. 10 MB)")

    try:
        # Step 1: OCR
        ocr_text = MathSolver.ocr_image(image_bytes)

        # Step 2: Classify content
        subject = classify_image_content(ocr_text)
        logger.info("Foto-Solver classified as: %s", subject)

        # Step 3: Route to correct solver
        if subject == "math":
            result = MathSolver.solve_from_image(image_bytes)
            result["classified_subject"] = "math"
            return result
        else:
            # Use Groq LLM for non-math subjects
            subject_prompts = {
                "physics": "Du bist ein Physik-Experte. Erklaere und loese die folgende Physik-Aufgabe Schritt fuer Schritt.",
                "chemistry": "Du bist ein Chemie-Experte. Erklaere und loese die folgende Chemie-Aufgabe Schritt fuer Schritt.",
                "biology": "Du bist ein Biologie-Experte. Erklaere das folgende biologische Konzept ausfuehrlich.",
                "text": "Erklaere den folgenden Text und beantworte moegliche Fragen dazu.",
            }
            prompt = subject_prompts.get(subject, subject_prompts["text"])
            explanation = call_groq_llm(
                prompt=f"Erkannter Text aus Bild:\n{ocr_text}",
                system_prompt=prompt,
                subject=subject,
                level="intermediate",
                language="de",
                task_type="explanation",
            )
            return {
                "ocr_text": ocr_text,
                "equations": [],
                "results": [],
                "classified_subject": subject,
                "formatted_response": f"## Erkanntes Fach: {subject.title()}\n\n**Erkannter Text:**\n> {ocr_text[:500]}\n\n{explanation}",
            }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/solve-text")
async def solve_from_text(
    equation: str = Form(...),
    _user: dict = Depends(get_current_user),
) -> dict:
    """Solve a math equation provided as text (no OCR needed).

    Input: equation string like "2x + 3 = 7" or "x^2 - 4 = 0".
    Returns: step-by-step solution in Markdown+KaTeX.
    """
    if not equation.strip():
        raise HTTPException(status_code=400, detail="Gleichung darf nicht leer sein")

    result = MathSolver.solve_from_text(equation.strip())
    return result
