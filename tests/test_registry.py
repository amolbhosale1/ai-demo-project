from briefing_agent.sources.registry import enforce_source_mix
from briefing_agent.types import BriefingItem


def _item(idx: int, source_type: str) -> BriefingItem:
    return BriefingItem(
        title=f"title {idx}",
        url=f"https://example.com/{idx}",
        summary="summary",
        source_name="test",
        source_type=source_type,
        category="article",
        score=10 - idx,
    )


def test_enforce_source_mix_minimums():
    ranked = [
        _item(1, "rss"),
        _item(2, "rss"),
        _item(3, "rss"),
        _item(4, "api"),
        _item(5, "api"),
        _item(6, "other"),
        _item(7, "other"),
        _item(8, "other"),
    ]
    selected = enforce_source_mix(ranked, target_count=8, minimum_share={"rss": 0.25, "api": 0.25, "other": 0.25})
    assert len(selected) == 8
    counts = {"rss": 0, "api": 0, "other": 0}
    for item in selected:
        counts[item.source_type] += 1
    assert counts["rss"] >= 2
    assert counts["api"] >= 2
    assert counts["other"] >= 2

