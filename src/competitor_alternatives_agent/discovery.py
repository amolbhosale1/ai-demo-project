from __future__ import annotations

import os
import re
import asyncio
import threading
from functools import lru_cache
from urllib.parse import urlparse

from competitor_alternatives_agent.types import ClientSnapshot, Competitor
from competitor_alternatives_agent.mcp_tools import load_mcp_servers_sync

_MCP_TOOLS_LOCK = threading.Lock()


def build_client_snapshot(cfg: dict) -> ClientSnapshot:
    profile = cfg.get("firm_profile", {})
    return ClientSnapshot(
        name=cfg.get("client_name", "Unknown Client"),
        website=profile.get("website", ""),
        services=list(profile.get("services", [])),
        target_sectors=list(profile.get("target_sectors", [])),
        priority_topics=list(profile.get("priority_topics", [])),
        geo_focus=list(profile.get("geo_focus", [])),
    )


def _normalize_slug(value: str) -> str:
    return value.lower().replace(" ", "-").replace("/", "-")


def _site_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "").strip()
    if not host:
        return "Unknown"
    base = host.split(".")[0].replace("-", " ").replace("_", " ")
    return base.title()


def _safe_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower().replace("www.", "")


def _extract_text_snippets(text: str, limit: int = 5) -> list[str]:
    low = text.lower()
    snippets: list[str] = []
    patterns = [
        r"(services?|solutions?|capabilities?)[:\s]+([^.\n]{30,160})",
        r"(industr(?:y|ies)|sectors?)[:\s]+([^.\n]{20,160})",
        r"(about us|what we do)[:\s]+([^.\n]{30,180})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, low):
            snippet = match.group(2).strip(" :-,")
            if snippet and snippet not in snippets:
                snippets.append(snippet)
                if len(snippets) >= limit:
                    return snippets
    return snippets


def _extract_urls_from_text(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s\]\)\"'>,]+", text or "", flags=re.IGNORECASE)
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        key = url.lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append(url)
    return out


def _coerce_output_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


@lru_cache(maxsize=1)
def _load_mcp_tools_registry():
    # Guard first-load race so MCP servers spawn once.
    with _MCP_TOOLS_LOCK:
        config_path = os.getenv("MCP_TOOLS_CONFIG", "config/tools_config.json").strip()
        tools = load_mcp_servers_sync(config_path, allowed_servers={"ddg-search"})
        if not tools:
            raise RuntimeError(f"No MCP tools loaded from '{config_path}'.")
        return tools


def _get_tool_by_names(*candidate_names: str):
    lowered = [name.lower() for name in candidate_names]
    tools = list(_load_mcp_tools_registry())
    # Prefer exact/suffixed matches first to avoid collisions.
    for tool in tools:
        tname = getattr(tool, "name", "").lower()
        if any(tname == name or tname.endswith(f"_{name}") for name in lowered):
            return tool
    # Fallback: fuzzy matching only for non-generic names.
    fuzzy_tokens = [name for name in lowered if name not in {"search", "fetch_content"} and len(name) > 5]
    for tool in tools:
        tname = getattr(tool, "name", "").lower()
        if any(token in tname for token in fuzzy_tokens):
            return tool
    available = [getattr(t, "name", "<unknown>") for t in tools]
    raise RuntimeError(f"Unable to find MCP tool among {candidate_names}. Available: {available}")


def _invoke_tool(tool, arguments: dict) -> str:
    # MCP-adapter StructuredTool instances are typically async-only.
    if hasattr(tool, "ainvoke"):
        out = asyncio.run(tool.ainvoke(arguments))
        return _coerce_output_text(out)
    if hasattr(tool, "invoke"):
        out = tool.invoke(arguments)
        return _coerce_output_text(out)
    raise RuntimeError(f"Tool '{getattr(tool, 'name', 'unknown')}' is not invokable.")


def _ddg_search_urls(query: str, max_results: int) -> list[str]:
    tool_name = os.getenv("DDG_MCP_SEARCH_TOOL", "search").strip()
    region = os.getenv("DDG_MCP_REGION", "").strip()
    tool = _get_tool_by_names(tool_name, "duckduckgo_search", "ddg_search", "search")
    # Prefer explicit DuckDuckGo schema first; fallback to schema-derived args if needed.
    args = {"query": query, "max_results": max_results}
    if region:
        args["region"] = region
    try:
        text = _invoke_tool(tool, args)
    except Exception as exc:
        # Some versions may not accept max_results/region. Retry with required-minimum arg.
        err = str(exc)
        if "unexpected keyword argument" in err.lower():
            text = _invoke_tool(tool, {"query": query})
        else:
            raise
    return _extract_urls_from_text(text)


def _ddg_fetch_content(url: str) -> str:
    tool_name = os.getenv("DDG_MCP_FETCH_TOOL", "fetch_content").strip()
    backend = os.getenv("DDG_MCP_FETCH_BACKEND", "").strip()
    args = {"url": url, "max_length": 5000}
    if backend:
        args["backend"] = backend
    tool = _get_tool_by_names(tool_name, "fetch_content")
    return _invoke_tool(tool, args)


def _extract_company_profile(url: str, bucket: str, client: ClientSnapshot) -> Competitor:
    content = _ddg_fetch_content(url)
    snippets = _extract_text_snippets(content) if content else []
    default_diffs = {
        "local": ["local expertise", "regional credibility", "market familiarity"],
        "similar": ["direct service overlap", "comparable ICP", "clear positioning"],
        "adjacent": ["different delivery model", "alternative buying path", "platform leverage"],
    }
    return Competitor(
        name=_site_name_from_url(url),
        website=url,
        category=bucket,
        geo=client.geo_focus[0] if client.geo_focus else "global",
        services=client.services[:3],
        target_sectors=client.target_sectors[:3],
        differentiators=snippets[:3] if snippets else default_diffs[bucket],
        evidence_urls=[url],
        source_bucket=bucket,
    )


def _mcp_discover_links(
    queries: list[str],
    max_results_per_query: int,
    min_links: int = 6,
) -> list[str]:
    # Preload tools once before fan-out to avoid repeated startup races.
    _load_mcp_tools_registry()
    links: list[str] = []
    seen: set[str] = set()
    errors: list[str] = []
    ddg_success = False
    min_links = max(1, min_links)
    # Sequential probing avoids long tail stalls from many concurrent 30s calls.
    for query in queries:
        try:
            result_links = _ddg_search_urls(query, max_results_per_query)
        except Exception as exc:
            errors.append(f"ddg: {exc}")
            continue
        if result_links:
            ddg_success = True
        for link in result_links:
            key = link.lower().rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            links.append(link)
        if len(links) >= min_links:
            break
    # DDG can intermittently return empty/blocked responses (e.g., temporary 403/202).
    # Return best-effort links and let downstream stages continue gracefully.
    if not links and errors:
        return []
    if not ddg_success:
        return []
    return links


def _directory_mode_queries(bucket: str, client: ClientSnapshot) -> list[str]:
    service = client.services[0] if client.services else "consulting"
    sector = client.target_sectors[0] if client.target_sectors else "business"
    geo = client.geo_focus[0] if client.geo_focus else "global"
    bases = [
        "clutch.co",
        "goodfirms.co",
        "g2.com",
        "designrush.com",
        "sortlist.com",
        "linkedin.com/company",
    ]
    bucket_hint = {
        "local": f"{service} {geo}",
        "similar": f"{service} {sector}",
        "adjacent": f"{sector} software alternatives",
    }[bucket]
    return [f"site:{base} {bucket_hint}" for base in bases]


def _discover_with_modes(
    client: ClientSnapshot,
    bucket: str,
    queries: list[str],
    max_results_per_query: int,
    max_queries_per_bucket: int,
    min_links: int,
) -> list[Competitor]:
    directory_queries = _directory_mode_queries(bucket, client)
    limit = max(1, max_queries_per_bucket)
    # Interleave query sources so capped runs still include base + directory intent.
    all_queries: list[str] = []
    max_len = max(len(queries), len(directory_queries))
    for i in range(max_len):
        if i < len(queries):
            all_queries.append(queries[i])
        if i < len(directory_queries):
            all_queries.append(directory_queries[i])
        if len(all_queries) >= limit:
            break
    all_queries = all_queries[:limit]

    raw_links = _mcp_discover_links(
        queries=all_queries,
        max_results_per_query=max_results_per_query,
        min_links=min_links,
    )

    candidates: list[Competitor] = []
    seen_domains: set[str] = set()
    client_domain = _safe_domain(client.website) if client.website else ""
    for link in raw_links:
        domain = _safe_domain(link)
        if not domain or domain == client_domain or domain in seen_domains:
            continue
        seen_domains.add(domain)
        candidates.append(
            _extract_company_profile(
                link,
                bucket=bucket,
                client=client,
            )
        )
    return candidates


def _discover_bucket(
    client: ClientSnapshot,
    bucket: str,
    queries: list[str],
    config: dict,
) -> list[Competitor]:
    max_results_per_query = int(config.get("max_results_per_query", 5))
    max_queries_per_bucket = int(config.get("max_queries_per_bucket", 8))
    min_links = int(config.get("min_links_per_bucket", 4))
    try:
        return _discover_with_modes(
            client=client,
            bucket=bucket,
            queries=queries,
            max_results_per_query=max_results_per_query,
            max_queries_per_bucket=max_queries_per_bucket,
            min_links=min_links,
        )
    except Exception:
        return []


def discover_local_competitors(client: ClientSnapshot, config: dict) -> list[Competitor]:
    local_cfg = config.get("local_competitors", [])
    if local_cfg:
        return [_from_cfg(item, "local") for item in local_cfg]
    geo = client.geo_focus[0] if client.geo_focus else "global"
    service = client.services[0] if client.services else "consulting"
    sector = client.target_sectors[0] if client.target_sectors else "business"
    queries = [
        f"{service} {sector} agency in {geo}",
        f"top {service} companies {geo}",
        f"linkedin {service} {geo}",
        f"site:clutch.co {service} {geo}",
    ]
    return _discover_bucket(client=client, bucket="local", queries=queries, config=config)


def discover_similar_competitors(client: ClientSnapshot, config: dict) -> list[Competitor]:
    similar_cfg = config.get("similar_competitors", [])
    if similar_cfg:
        return [_from_cfg(item, "similar") for item in similar_cfg]
    service = client.services[0] if client.services else "consulting"
    sector = client.target_sectors[0] if client.target_sectors else "business"
    queries = [
        f"best {service} companies for {sector}",
        f"{client.name} alternatives",
        f"{service} competitors",
        f"site:g2.com {service}",
    ]
    return _discover_bucket(client=client, bucket="similar", queries=queries, config=config)


def discover_adjacent_competitors(client: ClientSnapshot, config: dict) -> list[Competitor]:
    adjacent_cfg = config.get("adjacent_competitors", [])
    if adjacent_cfg:
        return [_from_cfg(item, "adjacent") for item in adjacent_cfg]
    service = client.services[0] if client.services else "consulting"
    sector = client.target_sectors[0] if client.target_sectors else "business"
    queries = [
        f"{service} alternatives platform",
        f"tools replacing {service}",
        f"{sector} automation platforms",
        f"site:linkedin.com/company {sector} software",
    ]
    return _discover_bucket(client=client, bucket="adjacent", queries=queries, config=config)


def _from_cfg(item: dict, bucket: str) -> Competitor:
    return Competitor(
        name=item.get("name", "Unknown Competitor"),
        website=item.get("website", ""),
        category=item.get("category", bucket),
        geo=item.get("geo", "global"),
        services=list(item.get("services", [])),
        target_sectors=list(item.get("target_sectors", [])),
        differentiators=list(item.get("differentiators", [])),
        evidence_urls=list(item.get("evidence_urls", [])),
        source_bucket=bucket,
    )

