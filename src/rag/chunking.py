"""Text chunking with recursive character splitting."""

from __future__ import annotations

from datetime import datetime, timezone

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.models import Chunk, Document


def chunk_documents(
    documents: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[Chunk]:
    """Split documents into overlapping chunks with GDPR metadata preserved."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    now = datetime.now(timezone.utc).isoformat()
    chunks: list[Chunk] = []
    for doc in documents:
        meta = doc.metadata or {}
        texts = splitter.split_text(doc.text)
        for piece in texts:
            chunks.append(
                Chunk(
                    text=piece,
                    source_file=doc.source_file,
                    doc_type=doc.doc_type,
                    subject_id=meta.get("subject_id"),
                    pseudonym=meta.get("pseudonym"),
                    data_category=meta.get("data_category", "workforce"),
                    lawful_basis=meta.get("lawful_basis", "legitimate_interest"),
                    purpose=meta.get("purpose", "hr_analytics"),
                    ingested_at=meta.get("ingested_at") or now,
                    restricted=bool(meta.get("restricted", False)),
                    page=meta.get("page"),
                )
            )
    return chunks


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
    """Split a raw string (used for simple PDF-only flows)."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_text(text)
