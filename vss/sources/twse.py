from __future__ import annotations

import httpx
from lxml import html

from vss.models import Evidence, SourceTier
from vss.normalize import normalize_name
from vss.sources.common import OK, UA, evidence

TIER = SourceTier.A
URL = "https://mops.twse.com.tw/mops/web/ajax_t51sb01"


async def lookup(name: str, country: str | None = None) -> list[Evidence]:
    if country and country.lower() not in ("taiwan", "tw", ""):
        return []
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.post(
            URL,
            data={"encodeURIComponent": "1", "step": "1", "firstin": "1", "TYPEK": "sii", "co_id": "", "keyword": name},
            headers=UA,
            timeout=10,
        )
    if r.status_code != OK:
        return []
    try:
        rows = html.fromstring(r.text).xpath("//tr[td]")
    except (ValueError, TypeError):
        return []
    target = normalize_name(name)
    for row in rows:
        cells = [" ".join(td.text_content().split()) for td in row.xpath("./td")]
        if len(cells) >= 2 and target in {normalize_name(c) for c in cells}:
            return [evidence("TWSE MOPS", TIER, "https://mops.twse.com.tw", " | ".join(cells[:5]))]
    return []
