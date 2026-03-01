"""OCR + Math Solver endpoints."""

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from app.core.auth import get_current_user
from app.services.ocr_solver import MathSolver

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post("/solve-image")
async def solve_from_image(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
) -> dict:
    """Upload an image of a math equation → OCR → Solve step-by-step.

    Accepts: JPEG, PNG, BMP, TIFF.
    Returns: OCR text, extracted equations, step-by-step solutions in Markdown+KaTeX.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Nur Bilddateien erlaubt (JPEG, PNG, etc.)")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="Datei zu gross (max. 10 MB)")

    try:
        result = MathSolver.solve_from_image(image_bytes)
        return result
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
