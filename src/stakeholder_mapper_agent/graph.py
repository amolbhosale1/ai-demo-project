from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from stakeholder_mapper_agent.connectors.generic import GenericConnector
from stakeholder_mapper_agent.connectors.india import IndiaConnector
from stakeholder_mapper_agent.connectors.uk import UKConnector
from stakeholder_mapper_agent.output.stakeholder_markdown import write_stakeholder_markdown
from stakeholder_mapper_agent.policy_scope import apply_user_theme_refinement, infer_policy_areas
from stakeholder_mapper_agent.profile import build_org_profile
from stakeholder_mapper_agent.scoring import merge_dedupe_and_score
from stakeholder_mapper_agent.output.stakeholder_xlsx import write_stakeholder_xlsx
from stakeholder_mapper_agent.types import OrganizationProfile, Stakeholder


class StakeholderMapperState(TypedDict):
    client_config: dict
    org_profile: OrganizationProfile | None
    policy_areas: list[str]
    raw_stakeholders: list[Stakeholder]
    scored_stakeholders: list[Stakeholder]
    output_path: str
    markdown_output_path: str


def build_stakeholder_mapper_graph():
    graph = StateGraph(StakeholderMapperState)
    graph.add_node("profile", _profile_node)
    graph.add_node("policy_scope", _policy_scope_node)
    graph.add_node("collect", _collect_node)
    graph.add_node("score", _score_node)
    graph.add_node("output", _output_node)
    graph.add_edge(START, "profile")
    graph.add_edge("profile", "policy_scope")
    graph.add_edge("policy_scope", "collect")
    graph.add_edge("collect", "score")
    graph.add_edge("score", "output")
    graph.add_edge("output", END)
    return graph.compile()


def _profile_node(state: StakeholderMapperState) -> StakeholderMapperState:
    state["org_profile"] = build_org_profile(state["client_config"])
    return state


def _policy_scope_node(state: StakeholderMapperState) -> StakeholderMapperState:
    inferred = infer_policy_areas(state["client_config"])
    state["policy_areas"] = apply_user_theme_refinement(inferred)
    return state


def _collect_node(state: StakeholderMapperState) -> StakeholderMapperState:
    profile = state["org_profile"]
    if profile is None:
        state["raw_stakeholders"] = []
        return state
    connector = _select_connector(profile.country_system)
    policy_areas = state.get("policy_areas", [])
    executive = connector.find_executive(profile, policy_areas)
    parliamentary = connector.find_parliamentary(profile, policy_areas)
    groups = connector.find_groups_and_committees(profile, policy_areas)
    state["raw_stakeholders"] = [*executive, *parliamentary, *groups]
    return state


def _score_node(state: StakeholderMapperState) -> StakeholderMapperState:
    profile = state["org_profile"]
    if profile is None:
        state["scored_stakeholders"] = []
        return state
    state["scored_stakeholders"] = merge_dedupe_and_score(state.get("raw_stakeholders", []), profile)
    return state


def _output_node(state: StakeholderMapperState) -> StakeholderMapperState:
    cfg = state["client_config"]
    mapper_cfg = cfg.get("stakeholder_mapper_agent", {})
    output_dir = mapper_cfg.get("output", {}).get("dir", "outputs")
    out = write_stakeholder_xlsx(
        output_dir=output_dir,
        client_name=cfg.get("client_name", "client"),
        stakeholders=state.get("scored_stakeholders", []),
    )
    md_out = write_stakeholder_markdown(
        output_dir=output_dir,
        client_name=cfg.get("client_name", "client"),
        stakeholders=state.get("scored_stakeholders", []),
    )
    state["output_path"] = str(out)
    state["markdown_output_path"] = str(md_out)
    return state


def _select_connector(country_system: str):
    key = (country_system or "").strip().lower()
    if key == "uk_parliamentary":
        return UKConnector()
    if key == "india_parliamentary":
        return IndiaConnector()
    return GenericConnector()


__all__ = ["build_stakeholder_mapper_graph", "_select_connector", "StakeholderMapperState"]

