from __future__ import annotations

from stakeholder_mapper_agent.types import OrganizationProfile


def build_org_profile(client_cfg: dict) -> OrganizationProfile:
    profile = client_cfg.get("firm_profile", {})
    mapper_cfg = client_cfg.get("stakeholder_mapper_agent", {})
    country = mapper_cfg.get("country", profile.get("geo_focus", ["global"])[0] if profile.get("geo_focus") else "global")
    country_system = mapper_cfg.get("country_system", _country_to_system(country))
    geography = mapper_cfg.get("geography", {})
    geography_scope = str(geography.get("scope", "country")).strip().lower()
    if geography_scope not in {"country", "state", "region"}:
        geography_scope = "country"
    target_regions = [str(x).strip() for x in geography.get("target_regions", []) if str(x).strip()]
    return OrganizationProfile(
        client_name=client_cfg.get("client_name", "Unknown Client"),
        country=country,
        country_system=country_system,
        geography_scope=geography_scope,
        target_regions=target_regions,
        services=profile.get("services", []),
        target_sectors=profile.get("target_sectors", []),
        priority_topics=profile.get("priority_topics", []),
        geo_focus=profile.get("geo_focus", []),
    )


def _country_to_system(country: str) -> str:
    value = (country or "").strip().lower()
    if value in {"uk", "united kingdom", "england", "scotland", "wales"}:
        return "uk_parliamentary"
    if value in {"india", "bharat"}:
        return "india_parliamentary"
    return "generic"

