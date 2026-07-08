"""Append-only JSONL audit logging (GDPR accountability)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """Write structured audit events; avoid storing raw PII by default."""

    def __init__(self, path: Path, log_pii: bool = False) -> None:
        self.path = path
        self.log_pii = log_pii
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def log(self, event: str, role: str, **details: Any) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "role": role,
        }
        record.update(details)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_query(self, question: str, role: str, **extra: Any) -> None:
        payload: dict[str, Any] = {
            "question_hash": self.hash_text(question),
        }
        if self.log_pii:
            payload["question"] = question
        payload.update(extra)
        self.log("query", role, **payload)

    def log_erasure(self, subject_id: int, role: str, deleted: int) -> None:
        self.log("erasure", role, subject_id=subject_id, deleted=deleted)

    def log_export(self, subject_id: int, role: str, count: int) -> None:
        self.log("export", role, subject_id=subject_id, count=count)

    def read_since(self, since_iso: str | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since_iso and str(obj.get("ts", "")) < since_iso:
                continue
            events.append(obj)
        return events
