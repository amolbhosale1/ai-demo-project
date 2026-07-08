"""HMAC-based pseudonymization for employee identifiers."""

from __future__ import annotations

import hashlib
import hmac


class Pseudonymizer:
    """Produce stable, non-reversible display tokens from subject IDs."""

    def __init__(self, salt: str, enabled: bool = True) -> None:
        self._key = salt.encode("utf-8")
        self.enabled = enabled

    def token(self, subject_id: int | str) -> str:
        digest = hmac.new(
            self._key,
            str(subject_id).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return digest[:8]

    def employee_label(self, subject_id: int | str) -> str:
        if not self.enabled:
            return f"Employee-{subject_id}"
        return f"Employee-{self.token(subject_id)}"

    def manager_label(self, subject_id: int | str) -> str:
        if not self.enabled:
            return f"Manager-{subject_id}"
        return f"Manager-{self.token(subject_id)}"
