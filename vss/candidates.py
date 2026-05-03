from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

import httpx

from vss.models import CandidateHypothesis, CandidateList, LocaleQueries, SearchCriteria, SearchQueries
from vss.normalize import normalize_domain, normalize_name
from vss.sources.common import fetch_json
from vss.sources.gleif import _JUNK as GLEIF_JUNK
from vss.sources.gleif import BASE as GLEIF_BASE
from vss.sources.gleif import _to_iso as gleif_iso
from vss.verify import match_country

if TYPE_CHECKING:
    from vss.llm import LLMClient

MAX_CANDIDATES = 5
OK = 200
_BAD_DOMAINS = {
    "reddit.com",
    "linkedin.com",
    "wikipedia.org",
    "crunchbase.com",
    "usnews.com",
    "forbes.com",
    "medium.com",
}
_RECOVERABLE = (httpx.HTTPError, ValueError, RuntimeError, TimeoutError)
_CJK = {"china", "taiwan", "japan", "korea", "south korea", "north korea"}


async def _build_search_queries(c: SearchCriteria, llm: LLMClient) -> list[str]:
    base = [c.raw_query] if c.raw_query else []
    prompt = (
        "Generate 3 web search queries for real supplier/company candidates. "
        f"Category: {c.product_category or 'any'}; country: {c.country or 'unspecified'}; "
        f"region: {c.region or 'unspecified'}; certifications: {', '.join(c.certifications) or 'none'}. "
        "Queries MUST be in English. Include the country name explicitly. Return JSON."
    )
    try:
        llm_qs = [q.strip() for q in (await llm.parse(SearchQueries, prompt)).queries if q.strip()][:3]
    except _RECOVERABLE:
        llm_qs = []
    return (base + llm_qs)[:4]


def _localized(q: str, loc: str) -> bool:
    if loc.lower() not in _CJK:
        return True
    chars = [c for c in q if not c.isspace()]
    return bool(chars) and sum(ord(c) > 127 for c in chars) / len(chars) >= 0.3


async def _locale_queries(c: SearchCriteria, llm: LLMClient) -> list[str]:
    loc = c.country or c.region
    if not loc:
        return []
    prompt = f"Generate 3 local-language search queries for finding {c.product_category} suppliers headquartered in {loc}. Return only query strings."
    try:
        return [q for q in (await llm.parse(LocaleQueries, prompt)).queries if _localized(q, loc)][:3]
    except _RECOVERABLE:
        return []


async def _tavily(q: str) -> list[dict]:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return []
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "https://api.tavily.com/search", json={"api_key": key, "query": q, "max_results": 10}, timeout=15
        )
    return r.json().get("results", []) if r.status_code == OK else []


async def _ddg(q: str) -> list[dict]:
    try:
        from ddgs import DDGS
        from ddgs.exceptions import DDGSException
    except ImportError:
        return []

    try:
        return await asyncio.to_thread(lambda: list(DDGS().text(q, max_results=10)))
    except DDGSException:
        return []


async def _brave(q: str) -> list[dict]:
    key = os.getenv("BRAVE_API_KEY")
    if not key:
        return []
    async with httpx.AsyncClient() as c:
        r = await c.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": q, "count": "10"},
            headers={"X-Subscription-Token": key, "Accept": "application/json"},
            timeout=10,
        )
    if r.status_code != OK:
        return []
    return [
        {"title": x.get("title", ""), "url": x.get("url", ""), "body": x.get("description", "")}
        for x in r.json().get("web", {}).get("results", [])[:10]
    ]


async def _search_all(queries: list[str]) -> list[dict]:
    res = await asyncio.gather(*(f(q) for q in queries for f in (_tavily, _ddg, _brave)), return_exceptions=True)
    return [x for r in res if isinstance(r, list) for x in r]


def _valid(c: CandidateHypothesis, criteria: SearchCriteria) -> bool:
    domain = normalize_domain(c.website)
    if not (2 <= len(c.name.strip()) <= 100) or domain in _BAD_DOMAINS:
        return False
    return not criteria.country or bool(c.country and match_country(c.country, criteria.country) == "VERIFIED")


async def _extract(results: list[dict], criteria: SearchCriteria, llm: LLMClient) -> list[CandidateHypothesis]:
    loc = criteria.country or criteria.region or "any region"
    snippets, seen = [], set()
    for r in results:
        url = r.get("url") or r.get("href", "")
        if url in seen:
            continue
        seen.add(url)
        snippets.append(
            f"Title: {r.get('title')}\nURL: {url}\nSnippet: {r.get('body') or r.get('content') or r.get('description')}"
        )
        if len(snippets) == 24:
            break
    prompt = (
        f"Extract up to {MAX_CANDIDATES} real supplier/company entities for: {criteria.product_category} in {loc}.\n"
        f"{'Headquarters country must be ' + criteria.country + '. ' if criteria.country else ''}"
        "Use search snippets as evidence; return only suppliers or manufacturers, never article titles, rankings, funds, people, products, or market reports. "
        "If HQ country is required but not evidenced for an entity, omit that entity. "
        "Return legal/trade name, root website if present, HQ country if evidenced.\n\n" + "\n---\n".join(snippets)
    )
    try:
        return [c for c in (await llm.parse(CandidateList, prompt)).candidates if _valid(c, criteria)]
    except _RECOVERABLE:
        return []


def _key(c: CandidateHypothesis) -> str:
    return normalize_domain(c.website) or normalize_name(c.name)


def _unique(candidates: list[CandidateHypothesis]) -> list[CandidateHypothesis]:
    out: dict[str, CandidateHypothesis] = {}
    for c in candidates:
        if k := _key(c):
            out.setdefault(k, c)
    return list(out.values())[:MAX_CANDIDATES]


async def _gleif_seed(criteria: SearchCriteria) -> list[CandidateHypothesis]:
    iso = gleif_iso(criteria.country)
    if not iso or not criteria.product_category:
        return []
    payload = await fetch_json(
        GLEIF_BASE,
        params={
            "filter[entity.legalAddress.country]": iso,
            "filter[fulltext]": criteria.product_category,
            "page[size]": "20",
        },
    )
    data = payload.get("data", []) if isinstance(payload, dict) else []
    out: list[CandidateHypothesis] = []
    for r in data:
        attrs = r.get("attributes", {})
        legal = attrs.get("entity", {}).get("legalName", {}).get("name", "")
        lei = attrs.get("lei", "")
        if not legal or any(w in legal.lower() for w in GLEIF_JUNK):
            continue
        out.append(
            CandidateHypothesis(
                name=legal,
                country=criteria.country,
                reason=f"GLEIF seed (LEI {lei})",
            )
        )
        if len(out) >= MAX_CANDIDATES:
            break
    return out


async def generate_candidates(criteria: SearchCriteria, llm: LLMClient) -> list[CandidateHypothesis]:
    seeds_task = asyncio.create_task(_gleif_seed(criteria))
    en = asyncio.create_task(_search_all(await _build_search_queries(criteria, llm)))
    local = await _locale_queries(criteria, llm)
    web = await _extract(await en + (await _search_all(local) if local else []), criteria, llm)
    return _unique(await seeds_task + web)
