from __future__ import annotations

from competitor_alternatives_agent.discovery import build_client_snapshot
from competitor_alternatives_agent import discovery
from competitor_alternatives_agent.gap_analysis import analyze_competitor_gaps
from competitor_alternatives_agent.output.report_markdown import write_competitor_report_markdown
from competitor_alternatives_agent.scoring import dedupe_and_rank, enforce_bucket_constraints
from competitor_alternatives_agent.types import Competitor


def _client_cfg() -> dict:
    return {
        "client_name": "Test Client",
        "firm_profile": {
            "website": "https://example.com",
            "services": ["mvp development", "web application development", "ai agent development"],
            "target_sectors": ["b2b saas", "healthcare software"],
            "priority_topics": ["delivery speed", "automation", "compliance"],
            "geo_focus": ["India", "UK"],
        },
    }


def test_bucket_counts_constraints():
    client = build_client_snapshot(_client_cfg())
    local = [
        Competitor("A", "", "local", "India", ["mvp development"], ["b2b saas"], ["delivery speed"], ["u"]),
        Competitor("B", "", "local", "India", ["mvp development"], ["b2b saas"], ["delivery speed"], ["u"]),
        Competitor("C", "", "local", "India", ["mvp development"], ["b2b saas"], ["delivery speed"], ["u"]),
        Competitor("D", "", "local", "India", ["mvp development"], ["b2b saas"], ["delivery speed"], ["u"]),
    ]
    similar = [Competitor(f"S{i}", "", "similar", "UK", ["web application development"], ["b2b saas"], ["automation"], ["u"]) for i in range(4)]
    adjacent = [Competitor(f"X{i}", "", "adjacent", "US", ["no-code"], ["b2b saas"], ["templates"], ["u"]) for i in range(6)]
    local_ranked = dedupe_and_rank(client, local, "local")
    similar_ranked = dedupe_and_rank(client, similar, "similar")
    adjacent_ranked = dedupe_and_rank(client, adjacent, "adjacent")
    local_out, similar_out, adjacent_out = enforce_bucket_constraints(local_ranked, similar_ranked, adjacent_ranked)
    assert len(local_out) == 3
    assert len(adjacent_out) == 4
    assert len(similar_out) == len(similar_ranked)


def test_dedupe_keeps_highest_scored():
    client = build_client_snapshot(_client_cfg())
    items = [
        Competitor("Dup", "https://dup.com", "similar", "UK", ["ai agent development"], ["b2b saas"], ["automation"], ["u"]),
        Competitor("Dup2", "https://dup.com", "similar", "UK", ["legacy migration"], ["public sector"], ["other"], ["u"]),
    ]
    ranked = dedupe_and_rank(client, items, "similar")
    assert len(ranked) == 1
    assert ranked[0].website == "https://dup.com"


def test_markdown_report_sections(tmp_path):
    client = build_client_snapshot(_client_cfg())
    local = [Competitor("Local One", "https://l1.com", "local", "India", ["mvp development"], ["b2b saas"], ["delivery speed"], ["u"])]
    local = analyze_competitor_gaps(client, local)
    out = write_competitor_report_markdown(client, local, [], [], ["Do first action"], tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "## Client Snapshot" in text
    assert "## Local Competitors (3)" in text
    assert "## Most Similar Competitors" in text
    assert "## Adjacent Competitors (4)" in text
    assert "## Competitor-By-Competitor Gap Analysis" in text
    assert "## Priority Actions (Next 30 Days)" in text


def test_discovery_uses_mcp_results(monkeypatch):
    client = build_client_snapshot(_client_cfg())

    def _mock_mcp_links(queries: list[str], max_results_per_query: int, min_links: int = 6) -> list[str]:
        return ["https://sample-one.com", "https://sample-two.com"]

    def _mock_extract(url: str, bucket: str, client):
        return Competitor(
            name=url.replace("https://", "").split(".")[0].title(),
            website=url,
            category=bucket,
            geo="India",
            services=["mvp development"],
            target_sectors=["b2b saas"],
            differentiators=["signal"],
            evidence_urls=[url],
            source_bucket=bucket,
        )

    monkeypatch.setattr(discovery, "_mcp_discover_links", _mock_mcp_links)
    monkeypatch.setattr(discovery, "_extract_company_profile", _mock_extract)

    results = discovery.discover_similar_competitors(
        client,
        config={},
    )
    assert results
    assert any(item.website == "https://sample-one.com" for item in results)


def test_directory_mode_parallel_path(monkeypatch):
    client = build_client_snapshot(_client_cfg())

    def _mock_mcp_links(queries: list[str], max_results_per_query: int, min_links: int = 6) -> list[str]:
        assert any("site:clutch.co" in q for q in queries)
        assert any("site:g2.com" in q for q in queries)
        return ["https://dir-one.com", "https://dir-two.com"]

    def _mock_extract(url: str, bucket: str, client):
        return Competitor(
            name="Dir",
            website=url,
            category=bucket,
            geo="India",
            services=["mvp development"],
            target_sectors=["b2b saas"],
            differentiators=["directory"],
            evidence_urls=[url],
            source_bucket=bucket,
        )

    monkeypatch.setattr(discovery, "_mcp_discover_links", _mock_mcp_links)
    monkeypatch.setattr(discovery, "_extract_company_profile", _mock_extract)
    results = discovery.discover_local_competitors(
        client,
        config={"max_results_per_query": 3},
    )
    assert len(results) == 2


def test_mcp_backend_discovery(monkeypatch):
    client = build_client_snapshot(_client_cfg())

    def _mock_mcp_links(queries: list[str], max_results_per_query: int, min_links: int = 6) -> list[str]:
        return ["https://mcp-one.com", "https://mcp-two.com"]

    def _mock_extract(url: str, bucket: str, client):
        return Competitor(
            name="Mcp",
            website=url,
            category=bucket,
            geo="UK",
            services=["web application development"],
            target_sectors=["b2b saas"],
            differentiators=["mcp"],
            evidence_urls=[url],
            source_bucket=bucket,
        )

    monkeypatch.setattr(discovery, "_mcp_discover_links", _mock_mcp_links)
    monkeypatch.setattr(discovery, "_extract_company_profile", _mock_extract)
    out = discovery.discover_similar_competitors(
        client,
        config={},
    )
    assert len(out) == 2

