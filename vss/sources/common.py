from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from vss.models import Evidence, SourceTier

OK = 200
UA = {"User-Agent": "Mozilla/5.0"}


def now() -> str:
    return datetime.now(UTC).isoformat()


def evidence(source: str, tier: SourceTier, url: str, snippet: str, fetched_at: str | None = None) -> Evidence:
    return Evidence(source=source, source_tier=tier, url=url, fetched_at=fetched_at or now(), snippet=snippet)


async def fetch_json(
    url: str,
    *,
    method: str = "GET",
    params: dict | None = None,
    json: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10,
    verify: bool = True,
    follow_redirects: bool = False,
) -> Any:
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=0.3, max=2),
            retry=retry_if_exception_type(httpx.TransportError),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(verify=verify, follow_redirects=follow_redirects) as c:
                    r = await c.request(method, url, params=params, json=json, headers=headers, timeout=timeout)
                if r.status_code != OK:
                    return None
                try:
                    return r.json()
                except ValueError:
                    return None
    except httpx.HTTPError:
        return None
    return None
