from __future__ import annotations

from typing import Protocol

from stakeholder_mapper_agent.types import OrganizationProfile, Stakeholder


class CountryConnector(Protocol):
    def find_executive(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        ...

    def find_parliamentary(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        ...

    def find_groups_and_committees(self, profile: OrganizationProfile, policy_areas: list[str]) -> list[Stakeholder]:
        ...

