"""RAG (Retrieval-Augmented Generation) service for EduAI Companion.

Uses FAISS for local vector similarity search and sentence-transformers
for generating embeddings. Documents and their metadata are persisted
to SQLite so the index survives restarts.

Embedding model: paraphrase-multilingual-MiniLM-L12-v2
  - Multilingual (German + English)
  - 384-dimensional embeddings
  - Fast inference, small footprint

German curriculum data sources for indexing:
  - LehrplanPLUS Bayern: https://www.lehrplanplus.bayern.de/
  - Bildungsserver Niedersachsen: https://cuvo.nibis.de/
  - Bildungsserver Hessen: https://kultusministerium.hessen.de/
  - KMK Bildungsstandards: https://www.kmk.org/themen/qualitaetssicherung-in-schulen/bildungsstandards.html
  - Wikipedia.de (filtered by education topics)
  - Khan Academy German transcripts
  - Abitur exam archives (past 5+ years, per Bundesland)
  - "Fachcurricula der Primar- und Sekundarstufe in Deutschland" dataset
"""
import json
import logging
import os
from typing import Optional

import aiosqlite
import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded globals (heavy imports deferred to first use)
_faiss_index = None
_embedding_model = None
_doc_ids: list[str] = []  # Maps FAISS row index -> doc_id

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
CHUNK_SIZE = 500  # tokens (approx 4 chars/token for German)
CHUNK_OVERLAP = 50

# Database path — co-located with the main SQLite DB
_DB_PATH: str | None = None


def _get_db_path() -> str:
    """Resolve the RAG database path, checking /data for Fly.io volume first."""
    global _DB_PATH
    if _DB_PATH:
        return _DB_PATH
    if os.path.isdir("/data"):
        _DB_PATH = "/data/rag.db"
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _DB_PATH = os.path.join(base, "rag.db")
    return _DB_PATH


def _get_embedding_model():
    """Lazy-load the sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def _get_faiss_index():
    """Lazy-load the FAISS index (flat L2)."""
    global _faiss_index
    if _faiss_index is None:
        import faiss
        _faiss_index = faiss.IndexFlatL2(EMBEDDING_DIM)
    return _faiss_index


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts into float32 vectors."""
    model = _get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return np.array(embeddings, dtype=np.float32)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks of roughly `chunk_size` tokens.

    Uses a simple word-based splitter (approx 1 word = 1.3 tokens for German).
    """
    words = text.split()
    # Approximate: 1 word ~ 1.3 tokens -> chunk_size tokens ~ chunk_size/1.3 words
    words_per_chunk = max(1, int(chunk_size / 1.3))
    overlap_words = max(0, int(overlap / 1.3))
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + words_per_chunk
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap_words
        if start >= len(words):
            break
    return chunks if chunks else [text.strip()]


# -- Database helpers --


async def _init_rag_db() -> aiosqlite.Connection:
    """Open the RAG database and create tables if needed."""
    db_path = _get_db_path()
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("""
        CREATE TABLE IF NOT EXISTS rag_documents (
            doc_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES rag_documents(doc_id) ON DELETE CASCADE,
            UNIQUE(doc_id, chunk_index)
        )
    """)
    await db.commit()
    return db


async def _rebuild_faiss_index() -> None:
    """Rebuild the FAISS index from all stored chunk embeddings."""
    global _doc_ids, _faiss_index
    import faiss

    db = await _init_rag_db()
    try:
        cursor = await db.execute(
            "SELECT doc_id, chunk_index, embedding FROM rag_chunks ORDER BY id"
        )
        rows = await cursor.fetchall()

        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        doc_ids: list[str] = []
        for row in rows:
            row_dict = dict(row)
            vec = np.frombuffer(row_dict["embedding"], dtype=np.float32).reshape(1, -1)
            index.add(vec)
            doc_ids.append(f"{row_dict['doc_id']}:{row_dict['chunk_index']}")

        _faiss_index = index
        _doc_ids = doc_ids
        logger.info("FAISS index rebuilt with %d vectors", index.ntotal)
    finally:
        await db.close()


# -- Public API --


async def index_document(
    doc_id: str,
    content: str,
    metadata: Optional[dict] = None,
) -> int:
    """Index a document: chunk it, embed chunks, store in FAISS + SQLite.

    Returns the number of chunks created.
    """
    global _doc_ids

    chunks = chunk_text(content)
    embeddings = embed_texts(chunks)

    db = await _init_rag_db()
    try:
        # Upsert document
        await db.execute(
            "INSERT OR REPLACE INTO rag_documents (doc_id, content, metadata) VALUES (?, ?, ?)",
            (doc_id, content, json.dumps(metadata or {}, ensure_ascii=False)),
        )
        # Remove old chunks for this doc
        await db.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))
        await db.commit()

        # Insert new chunks
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            await db.execute(
                "INSERT INTO rag_chunks (doc_id, chunk_index, chunk_text, embedding) VALUES (?, ?, ?, ?)",
                (doc_id, i, chunk, emb.tobytes()),
            )
        await db.commit()
    finally:
        await db.close()

    # Rebuild FAISS index from DB (simple approach, fine for <100k chunks)
    await _rebuild_faiss_index()
    return len(chunks)


async def search_similar(
    query: str,
    top_k: int = 3,
    filter_metadata: Optional[dict] = None,
) -> list[dict]:
    """Search for document chunks most similar to the query.

    Returns list of dicts: {doc_id, chunk_text, score, metadata, source}.
    """
    # Ensure index is built
    if _faiss_index is None or _faiss_index.ntotal == 0:
        await _rebuild_faiss_index()

    index = _get_faiss_index()
    if index.ntotal == 0:
        return []

    query_vec = embed_texts([query])
    # Search more than needed if we have to filter
    search_k = min(top_k * 3, index.ntotal)
    distances, indices = index.search(query_vec, search_k)

    db = await _init_rag_db()
    results: list[dict] = []
    try:
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(_doc_ids):
                continue
            ref = _doc_ids[idx]
            doc_id, chunk_idx = ref.rsplit(":", 1)

            # Fetch chunk text
            cursor = await db.execute(
                "SELECT chunk_text FROM rag_chunks WHERE doc_id = ? AND chunk_index = ?",
                (doc_id, int(chunk_idx)),
            )
            chunk_row = await cursor.fetchone()
            if not chunk_row:
                continue

            # Fetch document metadata
            cursor = await db.execute(
                "SELECT metadata FROM rag_documents WHERE doc_id = ?", (doc_id,)
            )
            doc_row = await cursor.fetchone()
            meta = json.loads(dict(doc_row)["metadata"]) if doc_row else {}

            # Apply metadata filter
            if filter_metadata:
                if not all(meta.get(k) == v for k, v in filter_metadata.items()):
                    continue

            results.append({
                "doc_id": doc_id,
                "chunk_text": dict(chunk_row)["chunk_text"],
                "score": float(dist),
                "metadata": meta,
                "source": meta.get("source", doc_id),
            })
            if len(results) >= top_k:
                break
    finally:
        await db.close()

    return results


async def get_document(doc_id: str) -> Optional[dict]:
    """Retrieve a single document by ID."""
    db = await _init_rag_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM rag_documents WHERE doc_id = ?", (doc_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        row_dict = dict(row)
        return {
            "doc_id": row_dict["doc_id"],
            "content": row_dict["content"],
            "metadata": json.loads(row_dict["metadata"]),
            "created_at": row_dict["created_at"],
        }
    finally:
        await db.close()


async def delete_document(doc_id: str) -> bool:
    """Delete a document and its chunks from the index."""
    db = await _init_rag_db()
    try:
        cursor = await db.execute(
            "SELECT doc_id FROM rag_documents WHERE doc_id = ?", (doc_id,)
        )
        if not await cursor.fetchone():
            return False
        await db.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))
        await db.execute("DELETE FROM rag_documents WHERE doc_id = ?", (doc_id,))
        await db.commit()
    finally:
        await db.close()

    await _rebuild_faiss_index()
    return True


async def list_documents() -> list[dict]:
    """List all indexed documents (without full content)."""
    db = await _init_rag_db()
    try:
        cursor = await db.execute(
            "SELECT doc_id, metadata, created_at FROM rag_documents ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {
                "doc_id": dict(r)["doc_id"],
                "metadata": json.loads(dict(r)["metadata"]),
                "created_at": dict(r)["created_at"],
            }
            for r in rows
        ]
    finally:
        await db.close()


async def get_stats() -> dict:
    """Return index statistics."""
    db = await _init_rag_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM rag_documents")
        doc_count = dict(await cursor.fetchone())["cnt"]
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM rag_chunks")
        chunk_count = dict(await cursor.fetchone())["cnt"]
        return {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "embedding_dim": EMBEDDING_DIM,
            "chunk_size": CHUNK_SIZE,
        }
    finally:
        await db.close()
