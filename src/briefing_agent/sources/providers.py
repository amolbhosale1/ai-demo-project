from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from briefing_agent.sources.economic import collect_world_bank_data
from briefing_agent.sources.other import collect_other_free_items
from briefing_agent.sources.rss import collect_rss_items
from briefing_agent.types import BriefingItem

ProviderFn = Callable[[dict[str, Any]], list[BriefingItem]]


def collect_from_providers(provider_specs: list[dict[str, Any]]) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    for spec in provider_specs:
        provider_name = spec.get("provider", "")
        config = spec.get("config", {})
        fn = _PROVIDER_REGISTRY.get(provider_name)
        if fn is None:
            continue
        try:
            items.extend(fn(config))
        except Exception:
            continue
    return items


def _collect_rss(config: dict[str, Any]) -> list[BriefingItem]:
    return collect_rss_items(
        feeds=config.get("feeds", []),
        max_items_per_feed=int(config.get("max_items_per_feed", 8)),
    )


def _collect_world_bank(config: dict[str, Any]) -> list[BriefingItem]:
    return collect_world_bank_data(
        indicators=config.get("indicators", []),
        max_points=int(config.get("max_points", 3)),
    )


def _collect_hn_algolia(config: dict[str, Any]) -> list[BriefingItem]:
    return collect_other_free_items(
        keywords=config.get("keywords", []),
        per_keyword=int(config.get("per_keyword", 3)),
    )


def _collect_json_endpoint(config: dict[str, Any]) -> list[BriefingItem]:
    """Generic free source connector for JSON feeds/APIs."""
    endpoint = config.get("url")
    source_name = config.get("source_name", "json-endpoint")
    source_type = config.get("source_type", "other")
    category = config.get("category", "article")
    if not endpoint:
        return []

    response = httpx.get(endpoint, timeout=float(config.get("timeout_sec", 20)))
    response.raise_for_status()
    payload = response.json()
    rows = payload if isinstance(payload, list) else payload.get(config.get("items_path", "items"), [])
    if not isinstance(rows, list):
        return []

    title_key = config.get("title_key", "title")
    url_key = config.get("url_key", "url")
    summary_key = config.get("summary_key", "summary")
    max_items = int(config.get("max_items", 10))
    items: list[BriefingItem] = []
    for row in rows[:max_items]:
        if not isinstance(row, dict):
            continue
        title = str(row.get(title_key, "")).strip()
        url = str(row.get(url_key, "")).strip()
        if not title or not url:
            continue
        items.append(
            BriefingItem(
                title=title,
                url=url,
                summary=str(row.get(summary_key, ""))[:500],
                source_name=source_name,
                source_type=source_type,
                category=category,
                metadata={"provider": "json_endpoint", "raw": row},
            )
        )
    return items


def _collect_mcp_gateway(config: dict[str, Any]) -> list[BriefingItem]:
    """
    Optional MCP-compatible connector.
    Expects an HTTP endpoint (from your own MCP gateway/proxy) that returns JSON.
    """
    mcp_url = config.get("gateway_url")
    if not mcp_url:
        return []
    proxy_config = {
        "url": mcp_url,
        "items_path": config.get("items_path", "items"),
        "title_key": config.get("title_key", "title"),
        "url_key": config.get("url_key", "url"),
        "summary_key": config.get("summary_key", "summary"),
        "source_name": config.get("source_name", "mcp-gateway"),
        "source_type": config.get("source_type", "other"),
        "category": config.get("category", "article"),
        "max_items": int(config.get("max_items", 10)),
        "timeout_sec": float(config.get("timeout_sec", 20)),
    }
    items = _collect_json_endpoint(proxy_config)
    for item in items:
        item.metadata["provider"] = "mcp_gateway"
    return items


_PROVIDER_REGISTRY: dict[str, ProviderFn] = {
    "rss_feed_loader": _collect_rss,
    "world_bank": _collect_world_bank,
    "hn_algolia": _collect_hn_algolia,
    "json_endpoint": _collect_json_endpoint,
    "mcp_gateway": _collect_mcp_gateway,
}

