"""Text extraction from various file formats (PDF, TXT, DOCX)."""

import os
import pdfplumber
from docx import Document


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from a plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    text_parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(file_path: str) -> str:
    """Extract text from a file based on its extension.

    Supported formats: .txt, .pdf, .docx

    Args:
        file_path: Path to the file.

    Returns:
        Extracted text content.

    Raises:
        ValueError: If the file format is not supported.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        return extract_text_from_txt(file_path)
    elif ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(
            f"Unsupported file format: '{ext}'. "
            "Supported formats: .txt, .pdf, .docx"
        )
