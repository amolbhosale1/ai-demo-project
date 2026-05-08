from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from competitor_alternatives_agent.types import ClientSnapshot, Competitor


def write_competitor_report_markdown(
    client: ClientSnapshot,
    local: list[Competitor],
    similar: list[Competitor],
    adjacent: list[Competitor],
    priority_actions: list[str],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_client = client.name.lower().replace(" ", "_")
    path = output_dir / f"{safe_client}_competitor_alternatives_{stamp}.md"
    lines: list[str] = []
    lines.append(f"# Competitor Alternatives Research Pack: {client.name}")
    lines.append("")
    lines.append("## Client Snapshot")
    lines.append(f"- Website: {client.website}")
    lines.append(f"- Services: {', '.join(client.services) if client.services else 'N/A'}")
    lines.append(f"- Target sectors: {', '.join(client.target_sectors) if client.target_sectors else 'N/A'}")
    lines.append(f"- Priority topics: {', '.join(client.priority_topics) if client.priority_topics else 'N/A'}")
    lines.append(f"- Geo focus: {', '.join(client.geo_focus) if client.geo_focus else 'N/A'}")
    lines.append("")
    lines.append("## Local Competitors (3)")
    lines.extend(_render_bucket(local))
    lines.append("")
    lines.append("## Most Similar Competitors")
    lines.extend(_render_bucket(similar))
    lines.append("")
    lines.append("## Adjacent Competitors (4)")
    lines.extend(_render_bucket(adjacent))
    lines.append("")
    lines.append("## Competitor-By-Competitor Gap Analysis")
    for competitor in local + similar + adjacent:
        lines.extend(_render_gap(competitor))
    lines.append("")
    lines.append("## Priority Actions (Next 30 Days)")
    for action in priority_actions:
        lines.append(f"- {action}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _render_bucket(items: list[Competitor]) -> list[str]:
    if not items:
        return ["- No competitors identified."]
    out: list[str] = []
    for c in items:
        out.append(f"- **{c.name}** ({c.geo})")
        out.append(f"  - Website: {c.website or 'N/A'}")
        out.append(f"  - Score: {c.score}")
        out.append(f"  - Services: {', '.join(c.services) if c.services else 'N/A'}")
        out.append(f"  - Evidence: {', '.join(c.evidence_urls) if c.evidence_urls else 'N/A'}")
    return out


def _render_gap(c: Competitor) -> list[str]:
    return [
        f"### {c.name}",
        f"- What they do right: {', '.join(c.strengths) if c.strengths else 'N/A'}",
        f"- What client currently misses: {', '.join(c.client_gaps) if c.client_gaps else 'N/A'}",
        f"- Suggested improvement: {c.suggested_improvement or 'N/A'}",
        f"- Call talking point: {c.call_talking_point or 'N/A'}",
        "",
    ]

