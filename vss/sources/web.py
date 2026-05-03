from __future__ import annotations

import asyncio
import os

from vss.models import Evidence, SourceTier
from vss.sources.common import evidence, fetch_json, now


async def _tavily(q: str) -> list[Evidence]:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return []
    payload = await fetch_json(
        "https://api.tavily.com/search",
        method="POST",
        json={"api_key": key, "query": q, "max_results": 5},
        timeout=15,
    )
    if not isinstance(payload, dict):
        return []
    fetched = now()
    return [
        evidence("Tavily", SourceTier.B, x.get("url", ""), (x.get("content") or "")[:300], fetched)
        for x in payload.get("results", [])[:5]
    ]


async def _ddg(q: str) -> list[Evidence]:
    try:
        from ddgs import DDGS
        from ddgs.exceptions import DDGSException
    except ImportError:
        return []

    try:
        results = await asyncio.to_thread(lambda: list(DDGS().text(q, max_results=5)))
    except DDGSException:
        return []
    fetched = now()
    return [
        evidence("DuckDuckGo", SourceTier.B, x.get("href", ""), (x.get("body") or "")[:300], fetched) for x in results
    ]


async def search(query: str) -> list[Evidence]:
    if not query.strip():
        return []
    a, b = await asyncio.gather(_tavily(query), _ddg(query))
    return a + b
