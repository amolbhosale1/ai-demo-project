from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Stakeholder:
    name: str
    stakeholder_type: str
    constituency_or_region: str
    country: str
    contact_information: str
    policy_area: str
    reason_for_relevance: str
    evidence_urls: list[str] = field(default_factory=list)
    source_bucket: str = "Executive_Stakeholders"
    relevance_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrganizationProfile:
    client_name: str
    country: str
    country_system: str
    geography_scope: str
    target_regions: list[str]
    services: list[str]
    target_sectors: list[str]
    priority_topics: list[str]
    geo_focus: list[str]

