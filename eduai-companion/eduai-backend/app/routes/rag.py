"""RAG (Retrieval-Augmented Generation) routes.

Endpoints for indexing documents, querying the vector store,
uploading files (PDF/text), and managing the RAG index.
"""
import hashlib
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


# ── Request / Response schemas ────────────────────────────────────


class IndexDocumentRequest(BaseModel):
    doc_id: Optional[str] = None
    content: str
    metadata: Optional[dict] = None


class IndexDocumentResponse(BaseModel):
    doc_id: str
    chunks_created: int


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 3
    filter_metadata: Optional[dict] = None


class RAGSearchResult(BaseModel):
    doc_id: str
    chunk_text: str
    score: float
    metadata: dict
    source: str


class RAGQueryResponse(BaseModel):
    results: list[RAGSearchResult]
    query: str


class RAGDocumentResponse(BaseModel):
    doc_id: str
    content: str
    metadata: dict
    created_at: str


class RAGStatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    embedding_model: str
    embedding_dim: int
    chunk_size: int


class RAGDocListItem(BaseModel):
    doc_id: str
    metadata: dict
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────


@router.post("/index", response_model=IndexDocumentResponse)
async def index_document(
    req: IndexDocumentRequest,
    current_user: dict = Depends(get_current_user),
):
    """Index a text document into the RAG vector store."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content must not be empty")

    doc_id = req.doc_id or hashlib.sha256(req.content[:200].encode()).hexdigest()[:16]
    metadata = req.metadata or {}
    metadata.setdefault("indexed_by", current_user["username"])

    chunks = await rag_service.index_document(
        doc_id=doc_id,
        content=req.content,
        metadata=metadata,
    )
    return IndexDocumentResponse(doc_id=doc_id, chunks_created=chunks)


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    req: RAGQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Search the RAG index for relevant document chunks."""
    results = await rag_service.search_similar(
        query=req.query,
        top_k=req.top_k,
        filter_metadata=req.filter_metadata,
    )
    return RAGQueryResponse(
        results=[RAGSearchResult(**r) for r in results],
        query=req.query,
    )


@router.post("/upload", response_model=IndexDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form("general"),
    language: str = Form("de"),
    source: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file (PDF or text) and index it into the RAG store.

    Supported formats: .txt, .md, .csv, .pdf
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    filename = file.filename.lower()
    content_bytes = await file.read()

    if filename.endswith(".pdf"):
        # Simple PDF text extraction — try to extract raw text
        text = _extract_pdf_text(content_bytes)
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from PDF. The file may be image-based.",
            )
    elif filename.endswith((".txt", ".md", ".csv")):
        text = content_bytes.decode("utf-8", errors="replace")
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Accepted: .txt, .md, .csv, .pdf",
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty or could not be read")

    doc_id = hashlib.sha256(content_bytes[:500]).hexdigest()[:16]
    metadata = {
        "filename": file.filename,
        "subject": subject,
        "language": language,
        "source": source or file.filename,
        "indexed_by": current_user["username"],
    }

    chunks = await rag_service.index_document(
        doc_id=doc_id,
        content=text,
        metadata=metadata,
    )
    return IndexDocumentResponse(doc_id=doc_id, chunks_created=chunks)


@router.get("/documents", response_model=list[RAGDocListItem])
async def list_documents(
    current_user: dict = Depends(get_current_user),
):
    """List all indexed documents."""
    docs = await rag_service.list_documents()
    return [RAGDocListItem(**d) for d in docs]


@router.get("/documents/{doc_id}", response_model=RAGDocumentResponse)
async def get_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a specific document by ID."""
    doc = await rag_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return RAGDocumentResponse(**doc)


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a document from the RAG index."""
    deleted = await rag_service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": f"Document {doc_id} deleted"}


@router.get("/stats", response_model=RAGStatsResponse)
async def get_stats(
    current_user: dict = Depends(get_current_user),
):
    """Get RAG index statistics."""
    stats = await rag_service.get_stats()
    return RAGStatsResponse(**stats)


@router.post("/seed")
async def seed_curriculum_data(
    current_user: dict = Depends(get_current_user),
):
    """Seed the RAG index with sample German curriculum data."""
    from app.services.seed_curriculum import seed_curriculum
    count = await seed_curriculum()
    return {"message": f"Seeded {count} curriculum documents", "documents_indexed": count}


# ── Helper functions ──────────────────────────────────────────────


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF file using basic binary parsing.

    This is a lightweight approach that works for text-based PDFs
    without requiring heavy dependencies like PyPDF2.
    Falls back to empty string for image-based PDFs.
    """
    try:
        # Simple extraction: look for text streams in the PDF binary
        text_parts: list[str] = []
        content = pdf_bytes.decode("latin-1")

        # Find text between BT (begin text) and ET (end text) operators
        import re
        # Match parenthesized text strings in PDF content streams
        for match in re.finditer(r"\(([^)]*)\)", content):
            part = match.group(1)
            # Filter out non-readable content
            if len(part) > 2 and any(c.isalpha() for c in part):
                text_parts.append(part)

        return " ".join(text_parts)
    except Exception as err:
        logger.warning("PDF text extraction failed: %s", err)
        return ""
