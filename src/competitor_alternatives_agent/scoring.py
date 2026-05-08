from __future__ import annotations

import re

from competitor_alternatives_agent.types import ClientSnapshot, Competitor


def _overlap_score(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    ls = {x.lower() for x in left}
    rs = {x.lower() for x in right}
    return len(ls & rs) / max(len(ls), 1)


def _geo_score(client: ClientSnapshot, competitor: Competitor, bucket: str) -> float:
    if bucket != "local":
        return 0.2
    focus = {x.lower() for x in client.geo_focus}
    return 1.0 if competitor.geo.lower() in focus else 0.1


def score_competitor(client: ClientSnapshot, competitor: Competitor, bucket: str) -> float:
    service_overlap = _overlap_score(client.services, competitor.services)
    sector_overlap = _overlap_score(client.target_sectors, competitor.target_sectors)
    topic_overlap = _overlap_score(client.priority_topics, competitor.differentiators)
    geo = _geo_score(client, competitor, bucket)
    if bucket == "adjacent":
        adjacency_boost = 1.0 - min(service_overlap, 0.8)
    else:
        adjacency_boost = 0.2
    base = (0.35 * service_overlap) + (0.25 * sector_overlap) + (0.2 * topic_overlap) + (0.1 * geo) + (0.1 * adjacency_boost)
    ai_boost = _ai_relevance_boost(client, competitor, bucket)
    return round(min(base + ai_boost, 1.0), 4)


def _tokenize(values: list[str]) -> set[str]:
    text = " ".join(values).lower()
    return set(re.findall(r"[a-z0-9\+\#\.]{3,}", text))


def _ai_relevance_boost(client: ClientSnapshot, competitor: Competitor, bucket: str) -> float:
    """
    Lightweight AI-like semantic boost without external model dependency.
    It rewards richer evidence and stronger lexical intent alignment.
    """
    client_terms = _tokenize(client.services + client.target_sectors + client.priority_topics + client.geo_focus)
    comp_terms = _tokenize(
        competitor.services
        + competitor.target_sectors
        + competitor.differentiators
        + competitor.evidence_urls
        + [competitor.name, competitor.geo, competitor.website, competitor.category]
    )
    if not client_terms or not comp_terms:
        return 0.0
    overlap_ratio = len(client_terms & comp_terms) / max(len(client_terms), 1)
    evidence_bonus = min(len(competitor.evidence_urls), 3) * 0.01
    directory_bonus = 0.02 if any(
        token in (competitor.website or "").lower()
        for token in ("clutch", "goodfirms", "g2.", "designrush", "sortlist", "linkedin.com/company")
    ) else 0.0
    bucket_bias = 0.01 if bucket == competitor.source_bucket else 0.0
    return min((0.08 * overlap_ratio) + evidence_bonus + directory_bonus + bucket_bias, 0.15)


def dedupe_and_rank(client: ClientSnapshot, competitors: list[Competitor], bucket: str) -> list[Competitor]:
    deduped: dict[str, Competitor] = {}
    for c in competitors:
        c.score = score_competitor(client, c, bucket)
        key = (c.website or c.name).lower()
        existing = deduped.get(key)
        if existing is None or c.score > existing.score:
            deduped[key] = c
    return sorted(deduped.values(), key=lambda item: item.score, reverse=True)


def enforce_bucket_constraints(
    local_candidates: list[Competitor],
    similar_candidates: list[Competitor],
    adjacent_candidates: list[Competitor],
    local_target: int = 3,
    adjacent_target: int = 4,
) -> tuple[list[Competitor], list[Competitor], list[Competitor]]:
    local = local_candidates[:local_target]
    adjacent = adjacent_candidates[:adjacent_target]
    similar = similar_candidates
    return local, similar, adjacent

