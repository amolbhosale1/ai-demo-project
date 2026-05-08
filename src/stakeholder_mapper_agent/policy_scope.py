from __future__ import annotations


def infer_policy_areas(client_cfg: dict) -> list[str]:
    mapper_cfg = client_cfg.get("stakeholder_mapper_agent", {})
    explicit = mapper_cfg.get("policy_areas", [])
    if explicit:
        return _dedupe(explicit)

    profile = client_cfg.get("firm_profile", {})
    industry = client_cfg.get("industry", {})
    candidates = [
        *profile.get("priority_topics", []),
        *profile.get("target_sectors", []),
        *industry.get("keywords", []),
    ]
    return _dedupe(candidates)[:15]


def apply_user_theme_refinement(policy_areas: list[str]) -> list[str]:
    if not policy_areas:
        return []
    print("\nStakeholder mapper inferred policy focus areas:")
    for idx, area in enumerate(policy_areas, start=1):
        print(f"{idx:02d}. {area}")
    print("\nUse these themes? (y/n)")
    ans = input("> ").strip().lower()
    if ans in {"y", "yes"}:
        return policy_areas

    print("Enter comma-separated indexes to keep (example: 1,3,4):")
    raw = input("> ").strip()
    keep_idx = {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
    chosen = [area for idx, area in enumerate(policy_areas, start=1) if idx in keep_idx]
    return chosen or policy_areas


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out

