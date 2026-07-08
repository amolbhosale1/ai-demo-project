"""Orchestrate dataset loading, chunking, embedding, and Qdrant upsert."""

from __future__ import annotations

from pathlib import Path

from rag.chunking import chunk_documents
from rag.config import Settings, get_settings
from rag.embeddings.ollama import OllamaEmbeddingClient
from rag.loaders.pdf_loader import PdfLoader
from rag.loaders.tabular_loader import TabularLoader
from rag.preprocessing import preprocess
from rag.vectorstore.qdrant import QdrantVectorStore


def build_vector_store(settings: Settings | None = None) -> QdrantVectorStore:
    settings = settings or get_settings()
    return QdrantVectorStore(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.qdrant_vector_size,
        api_key=settings.qdrant_api_key or None,
    )


def build_embedder(settings: Settings | None = None) -> OllamaEmbeddingClient:
    settings = settings or get_settings()
    return OllamaEmbeddingClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
    )


def ingest_dataset(
    settings: Settings | None = None,
    recreate: bool = True,
    batch_embed_size: int = 32,
) -> dict[str, int]:
    """Load PDF + CSVs, embed, and store in Qdrant. Returns counts."""
    settings = settings or get_settings()
    dataset_dir = Path(settings.rag_dataset_dir)

    pdf_path = dataset_dir / "hr_policy_detailed_5_pages.pdf"
    documents = []
    if pdf_path.exists():
        for doc in PdfLoader(pdf_path).load():
            doc.text = preprocess(doc.text)
            documents.append(doc)

    tabular = TabularLoader(dataset_dir, settings)
    for doc in tabular.load():
        doc.text = preprocess(doc.text)
        documents.append(doc)

    chunks = chunk_documents(
        documents,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )

    store = build_vector_store(settings)
    store.setup_collection(recreate=recreate)

    embedder = build_embedder(settings)
    total = 0
    for i in range(0, len(chunks), batch_embed_size):
        batch = chunks[i : i + batch_embed_size]
        vectors = embedder.embed([c.text for c in batch])
        # Validate vector size on first batch
        if vectors and len(vectors[0]) != settings.qdrant_vector_size:
            raise ValueError(
                f"Embedding dim {len(vectors[0])} != configured "
                f"QDRANT_VECTOR_SIZE {settings.qdrant_vector_size}"
            )
        total += store.upsert(batch, vectors)

    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "upserted": total,
    }
