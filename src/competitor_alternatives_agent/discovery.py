from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import quote_plus, urlparse

import feedparser
import httpx

from competitor_alternatives_agent.types import ClientSnapshot, Competitor


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


def _extract_links_from_duckduckgo_html(html: str) -> list[str]:
    links = re.findall(r'href="(https?://[^"]+)"', html, flags=re.IGNORECASE)
    cleaned: list[str] = []
    for link in links:
        if "duckduckgo.com" in link:
            continue
        if any(token in link.lower() for token in ("google.com", "youtube.com/watch", "facebook.com", "x.com/", "twitter.com/")):
            continue
        cleaned.append(unescape(link))
    # Preserve order while deduping.
    seen: set[str] = set()
    out: list[str] = []
    for link in cleaned:
        key = link.lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append(link)
    return out


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


def _fetch_url_text(url: str, timeout_s: float = 8.0) -> str:
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 competitor-research-bot"})
        if resp.status_code >= 400:
            return ""
        return resp.text
    except Exception:
        return ""


def _fetch_with_playwright(url: str, timeout_ms: int = 10_000) -> str:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        return ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            content = page.content()
            browser.close()
            return content
    except Exception:
        return ""


def _extract_company_profile(
    url: str,
    bucket: str,
    client: ClientSnapshot,
    enable_playwright: bool = False,
) -> Competitor:
    html = _fetch_url_text(url)
    if not html and enable_playwright:
        html = _fetch_with_playwright(url)
    snippets = _extract_text_snippets(html) if html else []
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


def _web_search(query: str, max_results: int) -> list[str]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    html = _fetch_url_text(url, timeout_s=10.0)
    if not html:
        return []
    return _extract_links_from_duckduckgo_html(html)[:max_results]


def _google_news_rss_links(query: str, max_results: int) -> list[str]:
    feed_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        parsed = feedparser.parse(feed_url)
        links: list[str] = []
        for entry in parsed.entries[: max_results * 2]:
            link = getattr(entry, "link", "") or ""
            if link.startswith("http"):
                links.append(link)
        # Deduplicate while preserving order.
        seen: set[str] = set()
        deduped: list[str] = []
        for link in links:
            key = link.lower().rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            deduped.append(link)
        return deduped[:max_results]
    except Exception:
        return []


def _discover_from_queries(
    client: ClientSnapshot,
    bucket: str,
    queries: list[str],
    max_results_per_query: int,
    enable_playwright: bool,
) -> list[Competitor]:
    candidates: list[Competitor] = []
    seen_domains: set[str] = set()
    client_domain = _safe_domain(client.website) if client.website else ""
    for query in queries:
        links = _web_search(query, max_results_per_query)
        links.extend(_google_news_rss_links(query, max_results=max(2, max_results_per_query // 2)))
        for link in links:
            domain = _safe_domain(link)
            if not domain or domain == client_domain or domain in seen_domains:
                continue
            seen_domains.add(domain)
            candidates.append(
                _extract_company_profile(
                    link,
                    bucket=bucket,
                    client=client,
                    enable_playwright=enable_playwright,
                )
            )
    if candidates:
        return candidates
    # Deterministic fallback when internet sources are unavailable.
    base = client.services[0] if client.services else "consulting"
    geo = client.geo_focus[0] if client.geo_focus else "global"
    out: list[Competitor] = []
    for idx in range(1, 7):
        out.append(
            Competitor(
                name=f"{bucket.title()} {base.title()} {idx}",
                website=f"https://example-{bucket}-{_normalize_slug(base)}-{idx}.com",
                category=bucket,
                geo=geo,
                services=client.services[:3],
                target_sectors=client.target_sectors[:3],
                differentiators=[f"{bucket} market focus", "clear messaging", "case-led positioning"],
                evidence_urls=[f"https://example.com/{bucket}/{idx}"],
                source_bucket=bucket,
            )
        )
    return out


def _discover_parallel_links(queries: list[str], max_results_per_query: int) -> list[str]:
    links: list[str] = []
    with ThreadPoolExecutor(max_workers=min(12, max(4, len(queries) * 2))) as executor:
        futures = []
        for query in queries:
            futures.append(executor.submit(_web_search, query, max_results_per_query))
            futures.append(executor.submit(_google_news_rss_links, query, max(2, max_results_per_query // 2)))
        for future in as_completed(futures):
            try:
                links.extend(future.result())
            except Exception:
                continue
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
    enable_playwright: bool,
    directory_mode: bool,
    parallel_fetch: bool,
) -> list[Competitor]:
    query_groups: list[list[str]] = [queries]
    if directory_mode:
        query_groups.append(_directory_mode_queries(bucket, client))
    all_queries = [q for group in query_groups for q in group]

    if parallel_fetch:
        raw_links = _discover_parallel_links(all_queries, max_results_per_query)
    else:
        raw_links = []
        for query in all_queries:
            raw_links.extend(_web_search(query, max_results_per_query))
            raw_links.extend(_google_news_rss_links(query, max_results=max(2, max_results_per_query // 2)))

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
                enable_playwright=enable_playwright,
            )
        )
    return candidates


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
    candidates = _discover_with_modes(
        client=client,
        bucket="local",
        queries=queries,
        max_results_per_query=int(config.get("max_results_per_query", 5)),
        enable_playwright=bool(config.get("enable_playwright", False)),
        directory_mode=bool(config.get("directory_mode", True)),
        parallel_fetch=bool(config.get("parallel_fetch", True)),
    )
    if candidates:
        return candidates
    return _discover_from_queries(
        client=client,
        bucket="local",
        queries=queries,
        max_results_per_query=int(config.get("max_results_per_query", 5)),
        enable_playwright=bool(config.get("enable_playwright", False)),
    )


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
    candidates = _discover_with_modes(
        client=client,
        bucket="similar",
        queries=queries,
        max_results_per_query=int(config.get("max_results_per_query", 5)),
        enable_playwright=bool(config.get("enable_playwright", False)),
        directory_mode=bool(config.get("directory_mode", True)),
        parallel_fetch=bool(config.get("parallel_fetch", True)),
    )
    if candidates:
        return candidates
    return _discover_from_queries(
        client=client,
        bucket="similar",
        queries=queries,
        max_results_per_query=int(config.get("max_results_per_query", 5)),
        enable_playwright=bool(config.get("enable_playwright", False)),
    )


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
    candidates = _discover_with_modes(
        client=client,
        bucket="adjacent",
        queries=queries,
        max_results_per_query=int(config.get("max_results_per_query", 5)),
        enable_playwright=bool(config.get("enable_playwright", False)),
        directory_mode=bool(config.get("directory_mode", True)),
        parallel_fetch=bool(config.get("parallel_fetch", True)),
    )
    if candidates:
        return candidates
    return _discover_from_queries(
        client=client,
        bucket="adjacent",
        queries=queries,
        max_results_per_query=int(config.get("max_results_per_query", 5)),
        enable_playwright=bool(config.get("enable_playwright", False)),
    )


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

