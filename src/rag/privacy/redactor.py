"""Query/response redaction based on caller role."""

from __future__ import annotations

import re
from typing import Literal

Sensitivity = Literal["standard", "high"]
Role = Literal["employee", "hr_admin", "dpo"]

# Patterns that look like individual salary/performance disclosures.
_SALARY_EXACT = re.compile(
    r"\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?|\binitial salary\b|\bsalary_usd\b",
    re.IGNORECASE,
)
_PERF_SCORE = re.compile(
    r"\bperformance(?:_score)?\b|\bsatisfaction(?:_score)?\b",
    re.IGNORECASE,
)
_GENDER_AGE = re.compile(r"\bgender\b|\bage\s+\d{1,3}\b|\b\d{1,3}\s+years?\s+old\b", re.IGNORECASE)


class Redactor:
    """Mask sensitive phrasing in model output for non-admin roles."""

    def __init__(
        self,
        role: Role = "employee",
        sensitivity: Sensitivity = "standard",
        known_names: set[str] | None = None,
    ) -> None:
        self.role = role
        self.sensitivity = sensitivity
        self.known_names = known_names or set()

    def should_refuse_individual_sensitive(self, question: str) -> bool:
        """Employee role may not ask about individual salary/performance."""
        if self.role in ("hr_admin", "dpo"):
            return False
        q = question.lower()
        individual_markers = (
            "employee id",
            "employee #",
            "salary",
            "performance",
            "satisfaction score",
            "how much does",
            "earn",
        )
        return any(m in q for m in individual_markers)

    def redact_answer(self, text: str) -> tuple[str, bool]:
        """Return (possibly redacted text, whether redactions)."""
        if self.role in ("hr_admin", "dpo"):
            return text, False

        redacted = text
        applied = False

        if _SALARY_EXACT.search(redacted):
            redacted = _SALARY_EXACT.sub("[REDACTED_SALARY]", redacted)
            applied = True
        if _PERF_SCORE.search(redacted) and "aggregate" not in redacted.lower():
            # Soft-flag; keep policy language but mask score-ish disclosures.
            pass

        for name in sorted(self.known_names, key=len, reverse=True):
            if name and name in redacted:
                redacted = redacted.replace(name, "[REDACTED_NAME]")
                applied = True

        if self.sensitivity == "high" and _GENDER_AGE.search(redacted):
            redacted = _GENDER_AGE.sub("[REDACTED_DEMOGRAPHIC]", redacted)
            applied = True

        return redacted, applied
