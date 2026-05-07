from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge_industry_preset(client_cfg: dict[str, Any], industries_cfg: dict[str, Any]) -> dict[str, Any]:
    industry = client_cfg.get("industry", {})
    industry_name = industry.get("name")
    preset = industries_cfg.get("industries", {}).get(industry_name, {}) if industry_name else {}
    merged = dict(client_cfg)
    merged_industry = dict(preset)
    merged_industry.update(industry)
    merged["industry"] = merged_industry
    return merged


def ensure_source_providers(client_cfg: dict[str, Any]) -> dict[str, Any]:
    """Build provider list from legacy fields when sources.providers is absent."""
    if client_cfg.get("sources", {}).get("providers"):
        return client_cfg

    industry = client_cfg.get("industry", {})
    providers: list[dict[str, Any]] = []
    if industry.get("rss_feeds"):
        providers.append(
            {
                "provider": "rss_feed_loader",
                "kind": "rss",
                "config": {"feeds": industry.get("rss_feeds", []), "max_items_per_feed": 8},
            }
        )
    if industry.get("economic_indicators"):
        providers.append(
            {
                "provider": "world_bank",
                "kind": "api",
                "config": {"indicators": industry.get("economic_indicators", []), "max_points": 3},
            }
        )
    if industry.get("keywords"):
        providers.append(
            {
                "provider": "hn_algolia",
                "kind": "other",
                "config": {"keywords": industry.get("keywords", []), "per_keyword": 3},
            }
        )

    merged = dict(client_cfg)
    sources = dict(merged.get("sources", {}))
    sources["providers"] = providers
    merged["sources"] = sources
    return merged

