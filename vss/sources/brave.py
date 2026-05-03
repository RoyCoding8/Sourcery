from __future__ import annotations

import os

from vss.models import Evidence, SourceTier
from vss.sources.common import evidence, fetch_json, now

TIER = SourceTier.B
URL = "https://api.search.brave.com/res/v1/web/search"


async def search(query: str) -> list[Evidence]:
    key = os.getenv("BRAVE_API_KEY")
    if not key or not query.strip():
        return []
    payload = await fetch_json(
        URL,
        params={"q": query, "count": "5"},
        headers={"X-Subscription-Token": key, "Accept": "application/json"},
    )
    if not isinstance(payload, dict):
        return []
    fetched = now()
    return [
        evidence("Brave Search", TIER, res.get("url", ""), (res.get("description") or "")[:300], fetched)
        for res in payload.get("web", {}).get("results", [])[:5]
    ]


async def lookup(name: str, country: str | None = None) -> list[Evidence]:
    return await search(f"{name} company" + (f" {country}" if country else ""))
