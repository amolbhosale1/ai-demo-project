"""Basic text preprocessing."""

from __future__ import annotations

import re


def preprocess(text: str) -> str:
    """Normalize whitespace for chunking."""
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()
