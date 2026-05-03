from __future__ import annotations

import csv
from pathlib import Path

from rapidfuzz import fuzz

from vss.models import Evidence, SourceTier
from vss.normalize import normalize_name
from vss.sources.common import evidence, now

SDN_PATH = Path(__file__).parent.parent.parent / "data" / "ofac_sdn.csv"
MATCH_THRESHOLD = 90

_cache: list[str] | None = None


def _load_sdn() -> list[str]:
    global _cache
    if _cache is not None:
        return _cache
    if not SDN_PATH.exists():
        _cache = []
        return _cache
    with SDN_PATH.open(encoding="utf-8", errors="ignore") as f:
        _cache = [row[1] for row in csv.reader(f) if len(row) > 1 and row[1].strip()]
    return _cache


async def lookup(name: str, _country: str | None = None) -> list[Evidence]:
    fetched = now()
    out = []
    nn = normalize_name(name)
    for sdn_name in _load_sdn():
        ns = normalize_name(sdn_name)
        exact = nn == ns
        if not exact and fuzz.token_set_ratio(name.lower(), sdn_name.lower()) < MATCH_THRESHOLD:
            continue
        out.append(
            evidence(
                "OFAC SDN" if exact else "OFAC SDN (potential)",
                SourceTier.A if exact else SourceTier.C,
                "https://sanctionssearch.ofac.treas.gov/",
                f"{'SANCTIONS HIT (exact)' if exact else 'POTENTIAL SANCTIONS MATCH (review required)'}: '{sdn_name}' matches '{name}'",
                fetched,
            )
        )
    return out
