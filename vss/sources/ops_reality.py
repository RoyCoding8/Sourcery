from __future__ import annotations

from datetime import UTC, datetime

from vss.models import Evidence, SourceTier
from vss.normalize import normalize_domain
from vss.sources.common import evidence, fetch_json, now

CRT_URL = "https://crt.sh/"
SOLID_AGE_YEARS = 3


def _parse(ts: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


async def lookup(_name: str, _country: str | None = None, url: str | None = None) -> list[Evidence]:
    domain = normalize_domain(url)
    if not domain:
        return []
    payload = await fetch_json(CRT_URL, params={"q": domain, "output": "json"}, timeout=15)
    if not isinstance(payload, list) or not payload:
        return []
    not_befores = [_parse(p.get("not_before", "")) for p in payload if p.get("not_before")]
    not_befores = [d for d in not_befores if d]
    if not not_befores:
        return []
    earliest = min(not_befores)
    n_certs = len({p.get("id") for p in payload})
    age_years = (datetime.now(UTC) - earliest).days / 365
    tier = SourceTier.A if age_years >= SOLID_AGE_YEARS else SourceTier.B
    return [
        evidence(
            "Domain Authority",
            tier,
            f"https://crt.sh/?q={domain}",
            f"Domain {domain}: {n_certs} CT records since {earliest.date()} ({age_years:.1f} yr)",
            now(),
        )
    ]
