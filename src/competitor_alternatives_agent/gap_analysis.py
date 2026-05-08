from __future__ import annotations

from competitor_alternatives_agent.types import ClientSnapshot, Competitor


def analyze_competitor_gaps(client: ClientSnapshot, competitors: list[Competitor]) -> list[Competitor]:
    client_services = {s.lower() for s in client.services}
    client_topics = {t.lower() for t in client.priority_topics}
    analyzed: list[Competitor] = []
    for c in competitors:
        competitor_strengths = c.differentiators[:3] or ["clear value proposition", "focused ICP", "consistent proof points"]
        service_gaps = [s for s in c.services if s.lower() not in client_services][:3]
        topic_gaps = [t for t in c.differentiators if t.lower() not in client_topics][:2]
        c.strengths = competitor_strengths
        c.client_gaps = (service_gaps + topic_gaps)[:4] or ["limited public proof points compared to competitor"]
        c.suggested_improvement = _build_improvement(c)
        c.call_talking_point = _build_talking_point(client, c)
        analyzed.append(c)
    return analyzed


def _build_improvement(competitor: Competitor) -> str:
    top_gap = competitor.client_gaps[0] if competitor.client_gaps else "offer packaging"
    return f"Package and publish a clearer {top_gap} offer with concrete outcomes and case studies."


def _build_talking_point(client: ClientSnapshot, competitor: Competitor) -> str:
    strength = competitor.strengths[0] if competitor.strengths else "market clarity"
    return f"Position {client.name} against {competitor.name} by acknowledging their {strength} and showing a faster, lower-risk delivery path."


def prioritize_actions(local: list[Competitor], similar: list[Competitor], adjacent: list[Competitor]) -> list[str]:
    pool = sorted(local + similar[:3] + adjacent, key=lambda c: c.score, reverse=True)
    actions: list[str] = []
    for c in pool[:5]:
        actions.append(
            f"Create one battlecard for {c.name} focused on '{c.client_gaps[0] if c.client_gaps else 'positioning gap'}' and test in next sales calls."
        )
    if not actions:
        actions.append("No competitor data available; collect baseline competitor signals before next call cycle.")
    return actions

