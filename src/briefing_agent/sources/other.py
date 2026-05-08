from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from briefing_agent.types import BriefingItem


def collect_other_free_items(keywords: list[str], per_keyword: int = 3) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    total = len(keywords)
    max_workers = max(1, min(8, total))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_collect_single_keyword, idx, total, kw, per_keyword)
            for idx, kw in enumerate(keywords, start=1)
        ]
        for future in as_completed(futures):
            items.extend(future.result())
    print(f"[OTHER] Completed collection: {len(items)} total items from {total} keywords")
    return items


def _collect_single_keyword(idx: int, total: int, kw: str, per_keyword: int) -> list[BriefingItem]:
    print(f"[OTHER {idx}/{total}] Fetching Algolia HN for keyword: {kw}")
    url = f"https://hn.algolia.com/api/v1/search?query={kw}&tags=story"
    try:
        response = httpx.get(url, timeout=20.0)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f"[OTHER {idx}/{total}] Failed keyword '{kw}': {exc}")
        return []

    keyword_items: list[BriefingItem] = []
    for hit in data.get("hits", [])[:per_keyword]:
        title = hit.get("title") or "Hacker News story"
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        keyword_items.append(
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
    print(f"[OTHER {idx}/{total}] Collected {len(keyword_items)} items for keyword: {kw}")
    return keyword_items

