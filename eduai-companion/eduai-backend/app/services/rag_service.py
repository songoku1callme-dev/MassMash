"""RAG (Retrieval-Augmented Generation) service for EduAI Companion.

This module provides the interface and a dummy implementation for
document indexing and semantic search. When a real vector store
(Pinecone, FAISS, Chroma, etc.) is integrated, only the backend
of each method needs to change — the API stays the same.

TODO: Replace DummyRAGService with a real vector store implementation.

Recommended German curriculum data sources for future indexing:
  - LehrplanPLUS Bayern: https://www.lehrplanplus.bayern.de/
  - Bildungsserver Niedersachsen: https://cuvo.nibis.de/
  - Bildungsserver Hessen: https://kultusministerium.hessen.de/
  - KMK Bildungsstandards: https://www.kmk.org/themen/qualitaetssicherung-in-schulen/bildungsstandards.html
  - Wikipedia.de (filtered by education topics)
  - Khan Academy German transcripts
  - Abitur exam archives (past 5+ years, per Bundesland)
  - „Fachcurricula der Primar- und Sekundarstufe in Deutschland" dataset

Vector store options:
  - Pinecone (managed, free tier available): https://www.pinecone.io/
  - FAISS (local, Facebook AI): https://github.com/facebookresearch/faiss
  - ChromaDB (local, open-source): https://www.trychroma.com/
  - Weaviate (managed + self-hosted): https://weaviate.io/

Embedding models for German text:
  - sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  - deepset/gbert-base (German BERT)
  - intfloat/multilingual-e5-large
"""
from abc import ABC, abstractmethod
from typing import Optional


class RAGServiceBase(ABC):
    """Abstract interface for a RAG (Retrieval-Augmented Generation) service."""

    @abstractmethod
    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Index a document for later retrieval.

        Args:
            doc_id: Unique document identifier.
            content: The text content to index (will be embedded).
            metadata: Optional metadata (subject, grade_level, language, source, etc.).
        """
        ...

    @abstractmethod
    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """Search for documents similar to the query.

        Args:
            query: The search query string.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filters (e.g. {"subject": "math"}).

        Returns:
            List of dicts with keys: doc_id, content, score, metadata.
        """
        ...

    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[dict]:
        """Retrieve a single document by its ID.

        Args:
            doc_id: The document identifier.

        Returns:
            Dict with keys: doc_id, content, metadata — or None if not found.
        """
        ...

    @abstractmethod
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the index.

        Args:
            doc_id: The document identifier.

        Returns:
            True if the document was deleted, False if not found.
        """
        ...


class DummyRAGService(RAGServiceBase):
    """In-memory dummy RAG implementation.

    Uses simple keyword matching instead of real vector similarity.
    Replace this with Pinecone/FAISS/Chroma when ready.

    NOTE: Data is NOT persistent — lost on restart.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        self._store[doc_id] = {
            "doc_id": doc_id,
            "content": content,
            "metadata": metadata or {},
        }

    def search_similar(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """Simple keyword overlap scoring (placeholder for vector similarity)."""
        query_words = set(query.lower().split())
        scored: list[tuple[float, dict]] = []

        for doc in self._store.values():
            # Apply metadata filter
            if filter_metadata:
                match = all(
                    doc["metadata"].get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue

            doc_words = set(doc["content"].lower().split())
            overlap = len(query_words & doc_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {**doc, "score": round(score, 4)}
            for score, doc in scored[:top_k]
        ]

    def get_document(self, doc_id: str) -> Optional[dict]:
        return self._store.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self._store:
            del self._store[doc_id]
            return True
        return False


# Singleton instance — import this in other modules
rag_service = DummyRAGService()
