from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from stakeholder_mapper_agent.types import Stakeholder


def write_stakeholder_markdown(output_dir: str | Path, client_name: str, stakeholders: list[Stakeholder]) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(UTC)
    filename = f"{client_name.lower().replace(' ', '_')}_stakeholders_{now_utc.date()}.md"
    file_path = output_path / filename

    lines: list[str] = []
    lines.append(f"# Stakeholder Map - {client_name}")
    lines.append("")
    lines.append(f"- Generated (UTC): {now_utc.isoformat()}")
    lines.append(f"- Total stakeholders: {len(stakeholders)}")
    lines.append("")
    lines.append("## Relationship Network")
    lines.append("")
    lines.extend(_mermaid_network(client_name, stakeholders))
    lines.append("")
    lines.append("## Stakeholder Details")
    lines.append("")
    for bucket in ["Executive_Stakeholders", "Parliamentary_Stakeholders", "Groups_and_Committees"]:
        rows = [s for s in stakeholders if s.source_bucket == bucket]
        lines.append(f"### {bucket}")
        if not rows:
            lines.append("- No entries")
            lines.append("")
            continue
        for s in rows:
            evidence = ", ".join(s.evidence_urls) if s.evidence_urls else "N/A"
            lines.append(f"- **Name:** {s.name}")
            lines.append(f"  - Type: {s.stakeholder_type}")
            lines.append(f"  - Constituency/Region: {s.constituency_or_region}")
            lines.append(f"  - Country: {s.country}")
            lines.append(f"  - Contact: {s.contact_information}")
            lines.append(f"  - Policy Area: {s.policy_area}")
            lines.append(f"  - Reason: {s.reason_for_relevance}")
            lines.append(f"  - Evidence: {evidence}")
            lines.append(f"  - Relevance Score: {s.relevance_score}")
        lines.append("")

    file_path.write_text("\n".join(lines), encoding="utf-8")
    return file_path


def _mermaid_network(client_name: str, stakeholders: list[Stakeholder]) -> list[str]:
    out = ["```mermaid", "flowchart TD"]
    out.append(f'    Client["{_safe_label(client_name)}"]')
    seen: set[str] = set()
    for idx, s in enumerate(stakeholders, start=1):
        node_id = f"S{idx}"
        bucket_id = _bucket_id(s.source_bucket)
        if bucket_id not in seen:
            seen.add(bucket_id)
            out.append(f'    {bucket_id}["{_safe_label(s.source_bucket)}"]')
            out.append(f"    Client --> {bucket_id}")
        label = _safe_label(f"{s.name} ({s.policy_area})")
        out.append(f'    {node_id}["{label}"]')
        out.append(f"    {bucket_id} --> {node_id}")
    out.append("```")
    return out


def _bucket_id(bucket: str) -> str:
    if bucket == "Executive_Stakeholders":
        return "ExecutiveStakeholders"
    if bucket == "Parliamentary_Stakeholders":
        return "ParliamentaryStakeholders"
    return "GroupsAndCommittees"


def _safe_label(text: str) -> str:
    return text.replace('"', "'")

