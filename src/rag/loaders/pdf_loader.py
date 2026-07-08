"""PDF document loader."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from rag.models import Document


class PdfLoader:
    """Extract text from a PDF into Document objects (one per page)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[Document]:
        if not self.path.exists():
            raise FileNotFoundError(f"PDF not found: {self.path}")
        reader = PdfReader(str(self.path))
        docs: list[Document] = []
        for page_number, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text() or ""
            if not extracted.strip():
                continue
            docs.append(
                Document(
                    text=f"--- Page {page_number} ---\n{extracted}",
                    source_file=self.path.name,
                    doc_type="policy",
                    metadata={
                        "page": page_number,
                        "data_category": "policy",
                        "lawful_basis": "legitimate_interest",
                        "purpose": "hr_policy",
                        "restricted": False,
                    },
                )
            )
        return docs
