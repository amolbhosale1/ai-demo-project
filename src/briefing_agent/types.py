from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BriefingItem:
    title: str
    url: str
    summary: str
    source_name: str
    source_type: str  # rss | api | other
    category: str  # article | data_point
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

