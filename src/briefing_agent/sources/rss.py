from __future__ import annotations

from datetime import UTC, datetime

import feedparser
from langchain_community.document_loaders import RSSFeedLoader

from briefing_agent.types import BriefingItem


def collect_rss_items(feeds: list[dict], max_items_per_feed: int = 8) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    for feed in feeds:
        url = feed.get("url")
        name = feed.get("name", "rss")
        if not url:
            continue
        try:
            loader = RSSFeedLoader(urls=[url], nlp=False, show_progress_bar=False)
            docs = loader.load()
        except Exception:
            docs = []

        if not docs:
            items.extend(_collect_with_feedparser(url=url, source_name=name, max_items=max_items_per_feed))
            continue

        for doc in docs[:max_items_per_feed]:
            metadata = doc.metadata or {}
            title = str(metadata.get("title", "")).strip()
            link = str(metadata.get("link", "")).strip()
            if not title or not link:
                continue
            summary = (doc.page_content or "").strip()
            items.append(
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

