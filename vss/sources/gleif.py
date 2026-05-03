import re

import pycountry

from vss.models import Evidence, SourceTier
from vss.normalize import normalize_name
from vss.sources.common import evidence, fetch_json, now

BASE = "https://api.gleif.org/api/v1/lei-records"
_PAREN = re.compile(r"\(([^)]+)\)")
_JUNK = {"etf", "fund", "trust", "index", "sicav", "ucits", "investment"}
MAX = 5


def _to_iso(country: str | None) -> str | None:
    if not country:
        return None
    c = country.strip()
    if len(c) <= 3:
        c = c.upper()
    try:
        return pycountry.countries.lookup(c).alpha_2
    except LookupError:
        pass
    try:
        return pycountry.countries.search_fuzzy(c)[0].alpha_2
    except LookupError:
        return None


def _search_variants(name: str) -> list[str]:
    paren_match = _PAREN.search(name)
    short = _PAREN.sub("", name).strip()
    long = paren_match.group(1).strip() if paren_match else None
    variants = []
    if long:
        variants.append(long)
    if short and short != long:
        variants.append(short)
    if not variants:
        variants.append(name)
    return variants


def _classify(legal_name: str, query: str, rec_country: str, expected_iso: str | None) -> str:
    ln = legal_name.lower()
    if any(w in ln for w in _JUNK):
        return "reject"
    if expected_iso and rec_country != expected_iso:
        return "reject"
    return "exact" if normalize_name(query) == normalize_name(legal_name) else "potential"


async def _query_gleif(q: str, iso: str | None) -> list[dict]:
    params: dict[str, str] = {"filter[fulltext]": q, "page[size]": "10"}
    if iso:
        params["filter[entity.legalAddress.country]"] = iso
    payload = await fetch_json(BASE, params=params)
    return payload.get("data", []) if isinstance(payload, dict) else []


async def lookup(name: str, country: str | None = None) -> list[Evidence]:
    iso = _to_iso(country)
    variants = _search_variants(name)
    raw: list[dict] = []
    for q in variants:
        raw = await _query_gleif(q, iso)
        if raw:
            break
        if iso:
            raw = await _query_gleif(q, None)
            if raw:
                break
    if not raw:
        return []
    fetched, out, query = now(), [], variants[0]
    for rec in raw:
        ent = rec.get("attributes", {}).get("entity", {})
        lei = rec.get("attributes", {}).get("lei", "")
        legal = ent.get("legalName", {}).get("name", "")
        addr = ent.get("legalAddress", {})
        rc = addr.get("country", "")
        cls = _classify(legal, query, rc, iso)
        if cls == "reject":
            continue
        snippet = f"LEI: {lei} | {legal} | {addr.get('city', '')}, {rc}"
        out.append(
            evidence(
                "GLEIF" if cls == "exact" else "GLEIF (potential)",
                SourceTier.A if cls == "exact" else SourceTier.C,
                f"{BASE}?filter[lei]={lei}",
                snippet if cls == "exact" else f"POTENTIAL MATCH: {snippet}",
                fetched,
            )
        )
    return out[:MAX]
