from __future__ import annotations

from pathlib import Path

from langgraph.graph import END, StateGraph

from competitor_alternatives_agent.discovery import (
    build_client_snapshot,
    discover_adjacent_competitors,
    discover_local_competitors,
    discover_similar_competitors,
)
from competitor_alternatives_agent.gap_analysis import analyze_competitor_gaps, prioritize_actions
from competitor_alternatives_agent.output.report_markdown import write_competitor_report_markdown
from competitor_alternatives_agent.scoring import dedupe_and_rank, enforce_bucket_constraints
from competitor_alternatives_agent.types import CompetitorAlternativesState


def _load_client_node(state: CompetitorAlternativesState) -> CompetitorAlternativesState:
    state["client_snapshot"] = build_client_snapshot(state["client_config"])
    return state


def _discover_node(state: CompetitorAlternativesState) -> CompetitorAlternativesState:
    cfg = state["client_config"].get("competitor_alternatives_agent", {})
    client = state["client_snapshot"]
    assert client is not None
    state["local_candidates"] = discover_local_competitors(client, cfg)
    state["similar_candidates"] = discover_similar_competitors(client, cfg)
    state["adjacent_candidates"] = discover_adjacent_competitors(client, cfg)
    return state


def _rank_node(state: CompetitorAlternativesState) -> CompetitorAlternativesState:
    client = state["client_snapshot"]
    assert client is not None
    local_ranked = dedupe_and_rank(client, state["local_candidates"], "local")
    similar_ranked = dedupe_and_rank(client, state["similar_candidates"], "similar")
    adjacent_ranked = dedupe_and_rank(client, state["adjacent_candidates"], "adjacent")
    local, similar, adjacent = enforce_bucket_constraints(local_ranked, similar_ranked, adjacent_ranked)
    state["local_competitors"] = local
    state["similar_competitors"] = similar
    state["adjacent_competitors"] = adjacent
    return state


def _gap_node(state: CompetitorAlternativesState) -> CompetitorAlternativesState:
    client = state["client_snapshot"]
    assert client is not None
    state["local_competitors"] = analyze_competitor_gaps(client, state["local_competitors"])
    state["similar_competitors"] = analyze_competitor_gaps(client, state["similar_competitors"])
    state["adjacent_competitors"] = analyze_competitor_gaps(client, state["adjacent_competitors"])
    state["priority_actions"] = prioritize_actions(
        state["local_competitors"],
        state["similar_competitors"],
        state["adjacent_competitors"],
    )
    return state


def _output_node(state: CompetitorAlternativesState) -> CompetitorAlternativesState:
    cfg = state["client_config"].get("competitor_alternatives_agent", {})
    out_dir = Path(cfg.get("output", {}).get("dir", "outputs"))
    client = state["client_snapshot"]
    assert client is not None
    output_path = write_competitor_report_markdown(
        client=client,
        local=state["local_competitors"],
        similar=state["similar_competitors"],
        adjacent=state["adjacent_competitors"],
        priority_actions=state["priority_actions"],
        output_dir=out_dir,
    )
    state["output_path"] = str(output_path)
    return state


def build_competitor_alternatives_graph():
    graph = StateGraph(CompetitorAlternativesState)
    graph.add_node("load_client", _load_client_node)
    graph.add_node("discover", _discover_node)
    graph.add_node("rank", _rank_node)
    graph.add_node("gap_analysis", _gap_node)
    graph.add_node("output", _output_node)
    graph.set_entry_point("load_client")
    graph.add_edge("load_client", "discover")
    graph.add_edge("discover", "rank")
    graph.add_edge("rank", "gap_analysis")
    graph.add_edge("gap_analysis", "output")
    graph.add_edge("output", END)
    return graph.compile()

