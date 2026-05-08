from __future__ import annotations

from stakeholder_mapper_agent.types import OrganizationProfile, Stakeholder


def merge_dedupe_and_score(stakeholders: list[Stakeholder], profile: OrganizationProfile) -> list[Stakeholder]:
    deduped: dict[str, Stakeholder] = {}
    corpus_terms = _terms(profile)
    for stakeholder in stakeholders:
        key = f"{stakeholder.name.strip().lower()}::{stakeholder.policy_area.strip().lower()}::{stakeholder.country.strip().lower()}"
        score = _score(stakeholder, corpus_terms)
        stakeholder.relevance_score = score
        current = deduped.get(key)
        if current is None or score > current.relevance_score:
            deduped[key] = stakeholder
    out = list(deduped.values())
    out.sort(key=lambda s: s.relevance_score, reverse=True)
    return out


def _terms(profile: OrganizationProfile) -> list[str]:
    values = [*profile.services, *profile.target_sectors, *profile.priority_topics, *profile.geo_focus]
    return [v.lower() for v in values if str(v).strip()]


def _score(stakeholder: Stakeholder, terms: list[str]) -> float:
    text = " ".join(
        [
            stakeholder.name,
            stakeholder.stakeholder_type,
            stakeholder.policy_area,
            stakeholder.reason_for_relevance,
        ]
    ).lower()
    hits = sum(1 for term in terms if term in text)
    bucket_bonus = {
        "Executive_Stakeholders": 1.2,
        "Parliamentary_Stakeholders": 1.0,
        "Groups_and_Committees": 0.9,
    }.get(stakeholder.source_bucket, 0.8)
    return round(1.0 + hits + bucket_bonus, 3)

