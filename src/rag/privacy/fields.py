"""PII field registry and helpers for data minimization."""

from __future__ import annotations

# Fields considered personal data in the HR dataset.
PII_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "gender",
        "age",
        "education",
        "hire_date",
        "performance_score",
        "satisfaction_score",
        "initial_salary_usd",
        "salary_usd",
    }
)

# Dropped entirely when GDPR_SENSITIVITY=high (beyond pseudonymization).
HIGH_SENSITIVITY_DROP: frozenset[str] = frozenset({"gender", "age"})


def salary_band(amount: float) -> str:
    """Bucket an exact salary into a coarse band (data minimization)."""
    if amount < 40_000:
        return "under-40k"
    if amount < 60_000:
        return "40k-60k"
    if amount < 80_000:
        return "60k-80k"
    if amount < 100_000:
        return "80k-100k"
    if amount < 150_000:
        return "100k-150k"
    if amount < 200_000:
        return "150k-200k"
    if amount < 300_000:
        return "200k-300k"
    return "300k+"
