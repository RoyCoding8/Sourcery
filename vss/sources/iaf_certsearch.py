from __future__ import annotations

from vss.models import Evidence, SourceTier
from vss.sources.common import UA, evidence, fetch_json, now

TIER = SourceTier.A
URL = "https://www.iafcertsearch.org/api/search"


async def lookup(name: str, country: str | None = None) -> list[Evidence]:
    payload = await fetch_json(URL, params={"name": name} | ({"country": country} if country else {}), headers=UA)
    if payload is None:
        return []
    data = payload if isinstance(payload, list) else payload.get("results", [])
    fetched = now()
    return [
        evidence(
            "IAF CertSearch",
            TIER,
            "https://www.iafcertsearch.org",
            f"{rec.get('organization', '')} - {rec.get('standard', '')} by {rec.get('certBody', '')}",
            fetched,
        )
        for rec in data[:3]
    ]
