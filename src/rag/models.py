"""Domain models for documents, chunks, retrieval, and answers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Role = Literal["employee", "hr_admin", "dpo"]
DocType = Literal[
    "policy",
    "employee",
    "department",
    "location",
    "org_edge",
    "promotion",
    "salary",
]


class Document(BaseModel):
    """A source document prior to chunking."""

    text: str
    source_file: str
    doc_type: DocType
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """A text chunk ready for embedding and storage."""

    text: str
    source_file: str
    doc_type: DocType
    subject_id: int | None = None
    pseudonym: str | None = None
    data_category: str = "workforce"
    lawful_basis: str = "legitimate_interest"
    purpose: str = "hr_analytics"
    ingested_at: str = ""
    restricted: bool = False
    page: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": self.text,
            "source_file": self.source_file,
            "doc_type": self.doc_type,
            "data_category": self.data_category,
            "lawful_basis": self.lawful_basis,
            "purpose": self.purpose,
            "ingested_at": self.ingested_at,
            "restricted": self.restricted,
        }
        if self.subject_id is not None:
            payload["subject_id"] = self.subject_id
        if self.pseudonym is not None:
            payload["pseudonym"] = self.pseudonym
        if self.page is not None:
            payload["page"] = self.page
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


class RetrievalHit(BaseModel):
    """A single vector search hit."""

    text: str
    score: float
    source_file: str = ""
    doc_type: str = ""
    subject_id: int | None = None
    pseudonym: str | None = None
    restricted: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class RAGAnswer(BaseModel):
    """Structured answer from the RAG agent."""

    answer: str
    sources: list[str] = Field(default_factory=list)
    redactions_applied: bool = False
