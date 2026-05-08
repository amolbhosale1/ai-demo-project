from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import feedparser
from langchain_community.document_loaders import RSSFeedLoader

from briefing_agent.types import BriefingItem


def collect_rss_items(feeds: list[dict], max_items_per_feed: int = 8) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    total = len(feeds)
    max_workers = max(1, min(8, total))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_collect_single_feed, idx, total, feed, max_items_per_feed)
            for idx, feed in enumerate(feeds, start=1)
        ]
        for future in as_completed(futures):
            items.extend(future.result())
    print(f"[RSS] Completed collection: {len(items)} total items from {total} feeds")
    return items


def _safe_published(entry: dict) -> str:
    value = entry.get("published", "") or entry.get("publish_date", "")
    if value:
        return value
    return datetime.now(UTC).isoformat()


def _collect_with_feedparser(url: str, source_name: str, max_items: int) -> list[BriefingItem]:
    parsed = feedparser.parse(url)
    fallback_items: list[BriefingItem] = []
    for entry in parsed.entries[:max_items]:
        title = str(entry.get("title", "")).strip()
        link = str(entry.get("link", "")).strip()
        if not title or not link:
            continue
        summary = str(entry.get("summary", "") or entry.get("description", "")).strip()
        fallback_items.append(
            BriefingItem(
                title=title,
                url=link,
                summary=summary[:500],
                source_name=source_name,
                source_type="rss",
                category="article",
                metadata={"published": _safe_published(entry)},
            )
        )
    return fallback_items


def _collect_single_feed(idx: int, total: int, feed: dict, max_items_per_feed: int) -> list[BriefingItem]:
    url = feed.get("url")
    name = feed.get("name", "rss")
    if not url:
        print(f"[RSS {idx}/{total}] Skipping feed with no URL: {name}")
        return []
    print(f"[RSS {idx}/{total}] Fetching: {name} -> {url}")
    try:
        loader = RSSFeedLoader(urls=[url], nlp=False, show_progress_bar=False)
        docs = loader.load()
    except Exception as exc:
        print(f"[RSS {idx}/{total}] Loader error for {name}: {exc}. Trying feedparser fallback.")
        docs = []

    if not docs:
        fallback_items = _collect_with_feedparser(url=url, source_name=name, max_items=max_items_per_feed)
        print(f"[RSS {idx}/{total}] Fallback collected {len(fallback_items)} items from {name}")
        return fallback_items

    feed_items: list[BriefingItem] = []
    for doc in docs[:max_items_per_feed]:
        metadata = doc.metadata or {}
        title = str(metadata.get("title", "")).strip()
        link = str(metadata.get("link", "")).strip()
        if not title or not link:
            continue
        summary = (doc.page_content or "").strip()
        feed_items.append(
            BriefingItem(
                title=title,
                url=link,
                summary=summary[:500],
                source_name=name,
                source_type="rss",
                category="article",
                metadata={"published": _safe_published(metadata), "raw": metadata},
            )
        )
    print(f"[RSS {idx}/{total}] Collected {len(feed_items)} items from {name}")
    return feed_items

