from __future__ import annotations

import httpx

from briefing_agent.types import BriefingItem


def collect_other_free_items(keywords: list[str], per_keyword: int = 3) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    for kw in keywords:
        url = f"https://hn.algolia.com/api/v1/search?query={kw}&tags=story"
        try:
            response = httpx.get(url, timeout=20.0)
            response.raise_for_status()
            data = response.json()
        except Exception:
            continue
        for hit in data.get("hits", [])[:per_keyword]:
            title = hit.get("title") or "Hacker News story"
            link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            items.append(
                BriefingItem(
                    title=title,
                    url=link,
                    summary=(hit.get("story_text") or "")[:400],
                    source_name="Hacker News (Algolia)",
                    source_type="other",
                    category="article",
                    metadata={"keyword": kw},
                )
            )
    return items

