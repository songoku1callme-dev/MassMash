"""File upload router - handles document upload and text extraction."""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import FileUploadResponse
from app.file_handling import extract_text
from app.config import settings

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload a file and extract its text content.

    Supported formats: .txt, .pdf, .docx
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".txt", ".pdf", ".docx"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: '{ext}'. Supported: .txt, .pdf, .docx",
        )

    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size_mb:.1f} MB). Max: {settings.MAX_FILE_SIZE_MB} MB.",
        )

    # Save to temp file for processing
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}{ext}"
    temp_path = os.path.join(settings.UPLOAD_DIR, temp_filename)

    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        extracted = extract_text(temp_path)

        return FileUploadResponse(
            filename=file.filename,
            extracted_text=extracted,
            char_count=len(extracted),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
