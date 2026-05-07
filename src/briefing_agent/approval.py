from __future__ import annotations

from briefing_agent.types import BriefingItem


def prompt_for_approval(items: list[BriefingItem]) -> list[BriefingItem]:
    print("\nSuggested items:\n")
    for idx, item in enumerate(items, start=1):
        print(f"{idx:02d}. [{item.source_type}] {item.title}")
        print(f"    {item.url}")
    print("\nApprove all? (y/n)")
    answer = input("> ").strip().lower()
    if answer in {"y", "yes"}:
        return items

    print("Enter comma-separated indexes to keep (example: 1,2,5):")
    raw = input("> ").strip()
    keep: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            keep.add(int(part))
    approved: list[BriefingItem] = []
    for idx, item in enumerate(items, start=1):
        if idx in keep:
            approved.append(item)
    return approved

