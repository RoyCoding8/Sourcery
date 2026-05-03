from __future__ import annotations

from vss.models import Evidence, SourceTier
from vss.sources.common import evidence, fetch_json, now

TIER = SourceTier.A
URL = "https://data.gcis.nat.gov.tw/od/data/api/5F64D864-61CB-4D0D-8902-B4CFC290B059"


async def lookup(name: str, country: str | None = None) -> list[Evidence]:
    if country and country.lower() not in ("taiwan", "tw", ""):
        return []
    safe_name = name.replace("'", "''")
    payload = await fetch_json(
        URL,
        params={"$format": "json", "$filter": f"Company_Name like '{safe_name}'", "$top": "3"},
        verify=False,
    )
    if not isinstance(payload, list):
        return []
    fetched = now()
    return [
        evidence(
            "MOEA Taiwan",
            TIER,
            URL,
            f"{rec.get('Company_Name', '')} | ID: {rec.get('Business_Accounting_NO', '')}",
            fetched,
        )
        for rec in payload[:3]
    ]
