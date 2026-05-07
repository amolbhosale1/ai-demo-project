from __future__ import annotations

import httpx

from briefing_agent.types import BriefingItem


def collect_world_bank_data(indicators: list[dict], max_points: int = 3) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    for indicator in indicators:
        code = indicator.get("code")
        title = indicator.get("title", code or "indicator")
        if not code:
            continue
        url = (
            "https://api.worldbank.org/v2/country/WLD/indicator/"
            f"{code}?format=json&per_page=10"
        )
        try:
            response = httpx.get(url, timeout=20.0)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            continue
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            continue
        count = 0
        for row in payload[1]:
            value = row.get("value")
            year = row.get("date")
            if value is None:
                continue
            text = f"{title}: {value} ({year})"
            items.append(
                BriefingItem(
                    title=f"{title} ({year})",
                    url="https://data.worldbank.org/",
                    summary=text,
                    source_name="World Bank",
                    source_type="api",
                    category="data_point",
                    metadata={"indicator": code, "year": year, "value": value},
                )
            )
            count += 1
            if count >= max_points:
                break
    return items

