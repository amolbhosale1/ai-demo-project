"""Protocol interfaces for loaders, embeddings, and vector stores."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from rag.models import Chunk, Document, RetrievalHit


@runtime_checkable
class DocumentLoader(Protocol):
    def load(self) -> list[Document]:
        """Load documents from a source."""
        ...


@runtime_checkable
class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    def setup_collection(self, recreate: bool = True) -> None:
        """Ensure the collection exists."""
        ...

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        """Upsert chunk payloads with their vectors. Returns count written."""
        ...

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        subject_id: int | None = None,
    ) -> list[RetrievalHit]:
        """Similarity search, optionally filtered by subject_id."""
        ...

    def delete_by_subject(self, subject_id: int) -> int:
        """Hard-delete all points for a data subject. Returns count deleted."""
        ...

    def export_by_subject(self, subject_id: int) -> list[dict[str, Any]]:
        """Export all payloads for a data subject."""
        ...

    def purge_before(self, cutoff_iso: str) -> int:
        """Delete points with ingested_at before cutoff. Returns count deleted."""
        ...
