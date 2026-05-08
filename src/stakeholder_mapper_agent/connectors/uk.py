from __future__ import annotations

from stakeholder_mapper_agent.types import OrganizationProfile, Stakeholder


class UKConnector:
    def find_executive(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        region_label = _region_label(profile)
        return [
            Stakeholder(
                name="Cabinet Office Ministerial Team",
                stakeholder_type="Minister",
                constituency_or_region=region_label,
                country="United Kingdom",
                contact_information="https://www.gov.uk/government/organisations/cabinet-office",
                policy_area=_pick(policy_areas),
                reason_for_relevance=f"Cross-government coordination and policy delivery impact for {region_label}.",
                evidence_urls=["https://www.gov.uk/government/organisations/cabinet-office"],
                source_bucket="Executive_Stakeholders",
            ),
            Stakeholder(
                name="Department for Business and Trade Ministerial Team",
                stakeholder_type="Minister",
                constituency_or_region=region_label,
                country="United Kingdom",
                contact_information="https://www.gov.uk/government/organisations/department-for-business-and-trade",
                policy_area=_pick(policy_areas),
                reason_for_relevance=f"Business, trade, and growth policy relevance for {region_label}.",
                evidence_urls=["https://www.gov.uk/government/organisations/department-for-business-and-trade"],
                source_bucket="Executive_Stakeholders",
            ),
        ]

    def find_parliamentary(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        area = _pick(policy_areas)
        region_label = _region_label(profile)
        return [
            Stakeholder(
                name="Relevant MP Contributions (Hansard query)",
                stakeholder_type="MP",
                constituency_or_region=region_label,
                country="United Kingdom",
                contact_information="https://hansard.parliament.uk/",
                policy_area=area,
                reason_for_relevance=f"Parliamentary contributions tied to {area} for {region_label}.",
                evidence_urls=[f"https://hansard.parliament.uk/search?searchTerm={area.replace(' ', '%20')}"],
                source_bucket="Parliamentary_Stakeholders",
            )
        ]

    def find_groups_and_committees(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        area = _pick(policy_areas)
        region_label = _region_label(profile)
        return [
            Stakeholder(
                name="APPG discovery (topic-linked)",
                stakeholder_type="APPG",
                constituency_or_region=region_label,
                country="United Kingdom",
                contact_information="https://www.parallelparliament.co.uk/about-appgs",
                policy_area=area,
                reason_for_relevance=f"APPGs shape cross-party discussion for {area} in {region_label}.",
                evidence_urls=[f"https://www.parallelparliament.co.uk/search?phrase={area.replace(' ', '+')}"],
                source_bucket="Groups_and_Committees",
            ),
            Stakeholder(
                name="House of Commons Select Committees",
                stakeholder_type="Select Committee",
                constituency_or_region=region_label,
                country="United Kingdom",
                contact_information="https://committees.parliament.uk/",
                policy_area=area,
                reason_for_relevance=f"Committee scrutiny impacts policy/sector direction in {area} for {region_label}.",
                evidence_urls=["https://committees.parliament.uk/"],
                source_bucket="Groups_and_Committees",
            ),
        ]


def _pick(policy_areas: list[str]) -> str:
    return policy_areas[0] if policy_areas else "public policy"


def _region_label(profile: OrganizationProfile) -> str:
    if profile.geography_scope in {"state", "region"} and profile.target_regions:
        return ", ".join(profile.target_regions)
    return "UK"

