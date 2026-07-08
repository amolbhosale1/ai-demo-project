"""Retention helpers for storage limitation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class RetentionPolicy:
    """Compute retention cutoffs from a day count."""

    def __init__(self, retention_days: int) -> None:
        self.retention_days = max(1, retention_days)

    def cutoff_iso(self, now: datetime | None = None) -> str:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.retention_days)
        return cutoff.isoformat()

    def is_expired(self, ingested_at: str, now: datetime | None = None) -> bool:
        if not ingested_at:
            return False
        try:
            ts = datetime.fromisoformat(ingested_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        now = now or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts < now - timedelta(days=self.retention_days)
