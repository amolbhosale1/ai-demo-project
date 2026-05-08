from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from briefing_agent.types import BriefingItem


def collect_world_bank_data(indicators: list[dict], max_points: int = 3) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    total = len(indicators)
    max_workers = max(1, min(8, total))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_collect_single_indicator, idx, total, indicator, max_points)
            for idx, indicator in enumerate(indicators, start=1)
        ]
        for future in as_completed(futures):
            items.extend(future.result())
    print(f"[API] Completed collection: {len(items)} total data points from {total} indicators")
    return items


def _collect_single_indicator(idx: int, total: int, indicator: dict, max_points: int) -> list[BriefingItem]:
    code = indicator.get("code")
    title = indicator.get("title", code or "indicator")
    if not code:
        print(f"[API {idx}/{total}] Skipping indicator with no code: {title}")
        return []
    print(f"[API {idx}/{total}] Fetching World Bank indicator: {title} ({code})")
    url = (
        "https://api.worldbank.org/v2/country/WLD/indicator/"
        f"{code}?format=json&per_page=10"
    )
    try:
        response = httpx.get(url, timeout=20.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"[API {idx}/{total}] Failed {title} ({code}): {exc}")
        return []
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        print(f"[API {idx}/{total}] Unexpected payload format for {title} ({code})")
        return []

    indicator_items: list[BriefingItem] = []
    for row in payload[1]:
        value = row.get("value")
        year = row.get("date")
        if value is None:
            continue
        text = f"{title}: {value} ({year})"
        indicator_items.append(
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
        if len(indicator_items) >= max_points:
            break
    print(f"[API {idx}/{total}] Collected {len(indicator_items)} data points for {title} ({code})")
    return indicator_items

