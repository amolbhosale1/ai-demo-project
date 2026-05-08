from __future__ import annotations

from stakeholder_mapper_agent.types import OrganizationProfile, Stakeholder


class IndiaConnector:
    def find_executive(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        area = _pick(policy_areas)
        region_label = _region_label(profile)
        return [
            Stakeholder(
                name="Prime Minister's Office (PMO)",
                stakeholder_type="Executive Office",
                constituency_or_region=region_label,
                country="India",
                contact_information="https://www.pmindia.gov.in/en/",
                policy_area=area,
                reason_for_relevance=f"Top-level executive policy direction and coordination for {region_label}.",
                evidence_urls=["https://www.pmindia.gov.in/en/"],
                source_bucket="Executive_Stakeholders",
            ),
            Stakeholder(
                name="Ministry of Electronics and Information Technology (MeitY)",
                stakeholder_type="Ministry",
                constituency_or_region=region_label,
                country="India",
                contact_information="https://www.meity.gov.in/",
                policy_area=area,
                reason_for_relevance=f"Digital policy, technology regulation, and innovation ecosystem for {region_label}.",
                evidence_urls=["https://www.meity.gov.in/"],
                source_bucket="Executive_Stakeholders",
            ),
        ]

    def find_parliamentary(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        area = _pick(policy_areas)
        region_label = _region_label(profile)
        return [
            Stakeholder(
                name="Lok Sabha/Rajya Sabha Member Contributions",
                stakeholder_type="MP",
                constituency_or_region=region_label,
                country="India",
                contact_information="https://sansad.in/",
                policy_area=area,
                reason_for_relevance=f"Parliamentary debates/questions linked to {area} for {region_label}.",
                evidence_urls=[f"https://sansad.in/rs/search?q={area.replace(' ', '%20')}"],
                source_bucket="Parliamentary_Stakeholders",
            )
        ]

    def find_groups_and_committees(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        area = _pick(policy_areas)
        region_label = _region_label(profile)
        return [
            Stakeholder(
                name="Department-related Parliamentary Standing Committees",
                stakeholder_type="Standing Committee",
                constituency_or_region=region_label,
                country="India",
                contact_information="https://sansad.in/",
                policy_area=area,
                reason_for_relevance=f"Committee scrutiny and reports influence {area} for {region_label}.",
                evidence_urls=["https://sansad.in/"],
                source_bucket="Groups_and_Committees",
            )
        ]


def _pick(policy_areas: list[str]) -> str:
    return policy_areas[0] if policy_areas else "public policy"


def _region_label(profile: OrganizationProfile) -> str:
    if profile.geography_scope in {"state", "region"} and profile.target_regions:
        return ", ".join(profile.target_regions)
    return "India"

