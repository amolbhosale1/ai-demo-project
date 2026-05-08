from __future__ import annotations

from stakeholder_mapper_agent.types import OrganizationProfile, Stakeholder


class GenericConnector:
    def find_executive(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        out: list[Stakeholder] = []
        region_label = _region_label(profile)
        for area in policy_areas[:6]:
            out.append(
                Stakeholder(
                    name=f"{profile.country} Ministry Lead ({area})",
                    stakeholder_type="Minister/Department Lead",
                    constituency_or_region=region_label,
                    country=profile.country,
                    contact_information="Public ministry contact page",
                    policy_area=area,
                    reason_for_relevance=f"Likely executive owner for policy area: {area} ({region_label}).",
                    evidence_urls=[f"https://www.google.com/search?q={profile.country}+ministry+{area.replace(' ', '+')}"],
                    source_bucket="Executive_Stakeholders",
                )
            )
        return out

    def find_parliamentary(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        out: list[Stakeholder] = []
        region_label = _region_label(profile)
        for area in policy_areas[:6]:
            out.append(
                Stakeholder(
                    name=f"{profile.country} Parliamentary Member ({area})",
                    stakeholder_type="Parliamentarian",
                    constituency_or_region=region_label,
                    country=profile.country,
                    contact_information="Official parliament member directory",
                    policy_area=area,
                    reason_for_relevance=f"Active parliamentary relevance expected for: {area} ({region_label}).",
                    evidence_urls=[f"https://www.google.com/search?q={profile.country}+parliament+{area.replace(' ', '+')}"],
                    source_bucket="Parliamentary_Stakeholders",
                )
            )
        return out

    def find_groups_and_committees(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        out: list[Stakeholder] = []
        region_label = _region_label(profile)
        for area in policy_areas[:6]:
            out.append(
                Stakeholder(
                    name=f"{profile.country} Committee/Group ({area})",
                    stakeholder_type="Committee/Policy Group",
                    constituency_or_region=region_label,
                    country=profile.country,
                    contact_information="Official committee contact or clerk office",
                    policy_area=area,
                    reason_for_relevance=f"Committee/group influence over {area} ({region_label}).",
                    evidence_urls=[f"https://www.google.com/search?q={profile.country}+committee+{area.replace(' ', '+')}"],
                    source_bucket="Groups_and_Committees",
                )
            )
        return out


def _region_label(profile: OrganizationProfile) -> str:
    if profile.geography_scope in {"state", "region"} and profile.target_regions:
        return ", ".join(profile.target_regions)
    return profile.country

