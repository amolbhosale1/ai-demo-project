"""Qdrant-backed vector store with GDPR subject operations."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from rag.models import Chunk, RetrievalHit


class QdrantVectorStore:
    """Thin wrapper around Qdrant for upsert, search, and subject rights."""

    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str,
        vector_size: int,
        api_key: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"host": host, "port": port}
        if api_key:
            kwargs["api_key"] = api_key
        self.client = QdrantClient(**kwargs)
        self.collection_name = collection_name
        self.vector_size = vector_size

    def setup_collection(self, recreate: bool = True) -> None:
        exists = self.client.collection_exists(self.collection_name)
        if exists and recreate:
            self.client.delete_collection(self.collection_name)
            exists = False
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qm.VectorParams(
                    size=self.vector_size,
                    distance=qm.Distance.COSINE,
                ),
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="subject_id",
                field_schema=qm.PayloadSchemaType.INTEGER,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="doc_type",
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="ingested_at",
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch")
        points = [
            qm.PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload=chunk.to_payload(),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        # Batch upsert for large datasets
        batch_size = 64
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i : i + batch_size],
                wait=True,
            )
        return len(points)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        subject_id: int | None = None,
    ) -> list[RetrievalHit]:
        query_filter = None
        if subject_id is not None:
            query_filter = qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="subject_id",
                        match=qm.MatchValue(value=subject_id),
                    )
                ]
            )
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        hits: list[RetrievalHit] = []
        for point in result.points:
            payload = point.payload or {}
            hits.append(
                RetrievalHit(
                    text=str(payload.get("text", "")),
                    score=float(point.score or 0.0),
                    source_file=str(payload.get("source_file", "")),
                    doc_type=str(payload.get("doc_type", "")),
                    subject_id=payload.get("subject_id"),
                    pseudonym=payload.get("pseudonym"),
                    restricted=bool(payload.get("restricted", False)),
                    payload=dict(payload),
                )
            )
        return hits

    def delete_by_subject(self, subject_id: int) -> int:
        # Count first for audit reporting
        count_result = self.client.count(
            collection_name=self.collection_name,
            count_filter=qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="subject_id",
                        match=qm.MatchValue(value=subject_id),
                    )
                ]
            ),
            exact=True,
        )
        deleted = int(count_result.count)
        if deleted:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(
                        must=[
                            qm.FieldCondition(
                                key="subject_id",
                                match=qm.MatchValue(value=subject_id),
                            )
                        ]
                    )
                ),
            )
        return deleted

    def export_by_subject(self, subject_id: int) -> list[dict[str, Any]]:
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="subject_id",
                        match=qm.MatchValue(value=subject_id),
                    )
                ]
            ),
            limit=10_000,
            with_payload=True,
            with_vectors=False,
        )
        return [dict(r.payload or {}) for r in records]

    def purge_before(self, cutoff_iso: str) -> int:
        """Delete points whose ingested_at is before cutoff (ISO-8601 UTC).

        Uses scroll + client-side comparison because ingested_at is a keyword
        field and numeric Range filters are unreliable for ISO strings.
        """
        deleted = 0
        offset = None
        ids_to_delete: list[str | int] = []
        while True:
            records, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=["ingested_at"],
                with_vectors=False,
            )
            for record in records:
                payload = record.payload or {}
                ingested = str(payload.get("ingested_at", ""))
                if ingested and ingested < cutoff_iso:
                    ids_to_delete.append(record.id)
            if offset is None:
                break

        if ids_to_delete:
            batch_size = 256
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i : i + batch_size]
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=qm.PointIdsList(points=batch),
                )
            deleted = len(ids_to_delete)
        return deleted
