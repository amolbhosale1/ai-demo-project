"""Retrieve relevant context from Qdrant for a user query."""

from __future__ import annotations

import re

from rag.config import Settings, get_settings
from rag.embeddings.ollama import OllamaEmbeddingClient
from rag.ingest import build_embedder, build_vector_store
from rag.models import RetrievalHit
from rag.vectorstore.qdrant import QdrantVectorStore

_EMPLOYEE_ID_RE = re.compile(
    r"\bemployee(?:\s+id)?\s*[#:]?\s*(\d+)\b|\bid\s+(\d+)\b",
    re.IGNORECASE,
)


def extract_employee_id(query: str) -> int | None:
    match = _EMPLOYEE_ID_RE.search(query)
    if not match:
        return None
    for group in match.groups():
        if group:
            return int(group)
    return None


class Retriever:
    """Embed a query and return top-k hits as formatted context."""

    def __init__(
        self,
        store: QdrantVectorStore | None = None,
        embedder: OllamaEmbeddingClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.store = store or build_vector_store(self.settings)
        self.embedder = embedder or build_embedder(self.settings)

    def search(self, query: str, top_k: int | None = None, role: str = "employee") -> list[RetrievalHit]:
        top_k = top_k or self.settings.rag_top_k
        vector = self.embedder.embed([query])[0]
        subject_id = None
        if role in ("hr_admin", "dpo"):
            subject_id = extract_employee_id(query)

        hits = self.store.search(vector, top_k=top_k, subject_id=subject_id)
        # If filtered search returned nothing, fall back to open semantic search.
        if subject_id is not None and not hits:
            hits = self.store.search(vector, top_k=top_k, subject_id=None)

        if role == "employee":
            filtered = [h for h in hits if h.doc_type != "salary"]
            if filtered:
                return filtered
        return hits

    def format_context(self, hits: list[RetrievalHit]) -> str:
        if not hits:
            return "No relevant context found."
        parts: list[str] = []
        for i, hit in enumerate(hits, start=1):
            header = (
                f"[{i}] (score={hit.score:.4f}, source={hit.source_file}, "
                f"type={hit.doc_type}"
            )
            if hit.subject_id is not None and hit.pseudonym:
                header += f", subject_id={hit.subject_id}, pseudonym={hit.pseudonym}"
            header += ")"
            parts.append(f"{header}\n{hit.text}")
        return "\n\n".join(parts)
