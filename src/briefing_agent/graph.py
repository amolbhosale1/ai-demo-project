from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from briefing_agent.approval import prompt_for_approval
from briefing_agent.models.llm import LLMClient
from briefing_agent.output.docx_writer import write_docx
from briefing_agent.sources.providers import collect_from_providers
from briefing_agent.sources.registry import enforce_source_mix, rank_and_deduplicate, summarize_mix
from briefing_agent.types import BriefingItem


class AgentState(TypedDict):
    client_config: dict
    raw_items: list[BriefingItem]
    ranked_items: list[BriefingItem]
    suggested_items: list[BriefingItem]
    approved_items: list[BriefingItem]
    briefing_summary: str
    output_path: str
    mix_counts: dict[str, int]


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("collect", _collect_node)
    graph.add_node("rank", _rank_node)
    graph.add_node("approve", _approve_node)
    graph.add_node("summarize", _summarize_node)
    graph.add_node("output", _output_node)

    graph.add_edge(START, "collect")
    graph.add_edge("collect", "rank")
    graph.add_edge("rank", "approve")
    graph.add_edge("approve", "summarize")
    graph.add_edge("summarize", "output")
    graph.add_edge("output", END)
    return graph.compile()


def _collect_node(state: AgentState) -> AgentState:
    cfg = state["client_config"]
    providers = cfg.get("sources", {}).get("providers", [])
    state["raw_items"] = collect_from_providers(providers)
    return state


def _rank_node(state: AgentState) -> AgentState:
    cfg = state["client_config"]
    keywords = cfg.get("industry", {}).get("keywords", [])
    ranked = rank_and_deduplicate(state["raw_items"], keywords)
    target_count = int(cfg.get("selection", {}).get("target_items", 12))
    minimum_share = cfg.get("selection", {}).get("minimum_share", {})
    state["ranked_items"] = ranked
    suggested = enforce_source_mix(ranked, target_count, minimum_share)
    state["suggested_items"] = suggested
    state["mix_counts"] = summarize_mix(suggested)
    print(f"Source mix counts: {state['mix_counts']}")
    return state


def _approve_node(state: AgentState) -> AgentState:
    state["approved_items"] = prompt_for_approval(state["suggested_items"])
    return state


def _summarize_node(state: AgentState) -> AgentState:
    cfg = state["client_config"]
    llm_cfg = cfg.get("llm", {})
    client = LLMClient(
        provider=llm_cfg["provider"],
        model=llm_cfg["model"],
        fallback_models=llm_cfg.get("fallback_models", []),
    )
    state["briefing_summary"] = client.summarize(cfg.get("client_name", "Client"), state["approved_items"])
    return state


def _output_node(state: AgentState) -> AgentState:
    cfg = state["client_config"]
    path = write_docx(
        output_dir=cfg.get("output", {}).get("dir", "outputs"),
        client_name=cfg.get("client_name", "client"),
        summary=state["briefing_summary"],
        approved_items=state["approved_items"],
        mix_counts=state.get("mix_counts", {}),
    )
    state["output_path"] = str(path)
    return state

