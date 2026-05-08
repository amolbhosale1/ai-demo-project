from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


@dataclass
class ClientSnapshot:
    name: str
    website: str
    services: list[str]
    target_sectors: list[str]
    priority_topics: list[str]
    geo_focus: list[str]


@dataclass
class Competitor:
    name: str
    website: str
    category: str
    geo: str
    services: list[str]
    target_sectors: list[str]
    differentiators: list[str]
    evidence_urls: list[str]
    score: float = 0.0
    source_bucket: str = ""
    strengths: list[str] = field(default_factory=list)
    client_gaps: list[str] = field(default_factory=list)
    suggested_improvement: str = ""
    call_talking_point: str = ""


class CompetitorAlternativesState(TypedDict):
    client_config: dict
    client_snapshot: ClientSnapshot | None
    local_candidates: list[Competitor]
    similar_candidates: list[Competitor]
    adjacent_candidates: list[Competitor]
    local_competitors: list[Competitor]
    similar_competitors: list[Competitor]
    adjacent_competitors: list[Competitor]
    priority_actions: list[str]
    output_path: str

