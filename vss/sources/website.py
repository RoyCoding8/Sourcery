from __future__ import annotations

import httpx
import trafilatura
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from vss.models import Evidence, SourceTier
from vss.sources.common import OK, UA, evidence

TIER = SourceTier.B


async def lookup(_name: str, _country: str | None = None, url: str | None = None) -> list[Evidence]:
    if not url:
        return []
    text = ""
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=0.3, max=2),
            retry=retry_if_exception_type(httpx.TransportError),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(follow_redirects=True) as c:
                    r = await c.get(url, timeout=10, headers=UA)
                if r.status_code != OK:
                    return []
                text = trafilatura.extract(r.text) or ""
    except httpx.HTTPError:
        return []
    return [
        evidence("Company Website", TIER, url, text[:500] if text else "Website reachable but no content extracted")
    ]
