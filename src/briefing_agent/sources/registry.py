from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from briefing_agent.types import BriefingItem


def rank_and_deduplicate(items: Iterable[BriefingItem], keywords: list[str]) -> list[BriefingItem]:
    seen: set[str] = set()
    ranked: list[BriefingItem] = []
    lowered = [k.lower() for k in keywords]
    for item in items:
        key = item.url.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        text = f"{item.title} {item.summary}".lower()
        score = 1.0 + sum(1 for kw in lowered if kw and kw in text)
        if item.category == "data_point":
            score += 0.5
        item.score = score
        ranked.append(item)
    ranked.sort(key=lambda x: x.score, reverse=True)
    return ranked


def enforce_source_mix(
    ranked_items: list[BriefingItem],
    target_count: int,
    minimum_share: dict[str, float] | None = None,
) -> list[BriefingItem]:
    if minimum_share is None:
        minimum_share = {"rss": 0.25, "api": 0.25, "other": 0.25}
    buckets: dict[str, list[BriefingItem]] = defaultdict(list)
    for item in ranked_items:
        buckets[item.source_type].append(item)

    selected: list[BriefingItem] = []
    for source_type, share in minimum_share.items():
        min_count = int(target_count * share)
        if (target_count * share) - min_count > 0:
            min_count += 1
        selected.extend(buckets.get(source_type, [])[:min_count])

    selected_urls = {i.url for i in selected}
    for item in ranked_items:
        if len(selected) >= target_count:
            break
        if item.url in selected_urls:
            continue
        selected.append(item)
        selected_urls.add(item.url)

    return selected[:target_count]


def summarize_mix(items: list[BriefingItem]) -> dict[str, int]:
    counts: dict[str, int] = {"rss": 0, "api": 0, "other": 0}
    for item in items:
        if item.source_type in counts:
            counts[item.source_type] += 1
    return counts

