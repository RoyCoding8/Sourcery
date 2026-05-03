from __future__ import annotations

import logging
import re

import httpx
import pycountry

from vss.llm import LLMClient
from vss.models import SearchCriteria
from vss.semantics import certs as norm_certs
from vss.verify import match_country

log = logging.getLogger(__name__)
_RECOVERABLE = (httpx.HTTPError, ValueError, RuntimeError, TimeoutError)

_PARSE_PROMPT = """Extract structured search criteria from this supplier query.

Query: {query}

CRITICAL: If the query mentions a specific country (e.g., "China", "Taiwan", "US", "India", "UK"), you MUST extract it into the 'country' field. Do not leave it null.
Country adjectives and demonyms are country constraints: Chinese => China, Taiwanese => Taiwan, Japanese => Japan, Korean => South Korea unless North Korea is explicit, Vietnamese => Vietnam, American => United States, British => United Kingdom, Indian => India.
Respect negation: "not Chinese", "outside China", "excluding Taiwan" are NOT positive country constraints.

Return JSON matching the schema. For fields not mentioned, use null.
- product_category: what they make/supply (e.g. "semiconductors", "AI chips")
- region: geographic region (e.g. "Southeast Asia", "East Asia")
- country: specific country if mentioned (e.g. "Taiwan", "China", "US", "India")
- certifications: list of cert standards (e.g. ["ISO 9001", "CE"])
- min_employees / max_employees: headcount bounds if mentioned
- additional_filters: any other constraints as key-value pairs
- raw_query: the original query verbatim"""

_ALIASES = {
    "usa": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "us": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "prc": "China",
    "china": "China",
    "taiwan": "Taiwan",
    "south korea": "South Korea",
    "korea": "South Korea",
    "viet nam": "Vietnam",
    "vietnam": "Vietnam",
}
_REGIONS = ("southeast asia", "east asia", "south asia", "north america", "latin america", "europe", "emea", "apac")
_CERT = re.compile(r"\b(ISO\s?\d{3,5}(?::\d{4})?|IATF\s?16949|AS9100|CE|RoHS|REACH|GMP|HACCP|FDA)\b", re.I)
_EMP = re.compile(
    r"(?:at least|over|more than|min(?:imum)?\s*)\D*(\d[\d,]*)\+?\s*(?:employees|staff|workers|people)|(?:under|less than|max(?:imum)?\s*)\D*(\d[\d,]*)\s*(?:employees|staff|workers|people)",
    re.I,
)


def _conflict(c: SearchCriteria, msg: str) -> None:
    log.warning("parser conflict: %s", msg)
    old = c.additional_filters.get("_parser_conflict")
    c.additional_filters["_parser_conflict"] = f"{old}; {msg}" if old else msg


def _country(query: str) -> str:
    q = query.lower()

    def neg(name: str):
        return re.search(rf"\b(?:not|excluding|outside|except)\s+(?:in\s+|from\s+|of\s+)?{re.escape(name)}\b", q)

    for k, v in sorted(_ALIASES.items(), key=lambda x: -len(x[0])):
        if neg(k):
            continue
        if re.search(rf"\b(?:in|from|of|based in|headquartered in)\s+{re.escape(k)}\b", q):
            return v
    for c in pycountry.countries:
        names = [getattr(c, x, "") for x in ("name", "common_name", "official_name")]
        if any(n and neg(n.lower()) for n in names):
            continue
        if any(
            n and re.search(rf"\b(?:in|from|of|based in|headquartered in)\s+{re.escape(n.lower())}\b", q) for n in names
        ):
            return c.name
    return ""


def _region(query: str) -> str:
    q = query.lower()
    return next((r.title() for r in _REGIONS if re.search(rf"\b{re.escape(r)}\b", q)), "")


def _certs(query: str) -> list[str]:
    out = []
    for m in _CERT.finditer(query):
        pre = query[max(0, m.start() - 16) : m.start()].lower()
        if re.search(r"\b(no|not|without|excluding)\b", pre):
            continue
        out.extend(norm_certs(m.group(0)))
    return list(dict.fromkeys(out))


def _employees(query: str) -> tuple[int | None, int | None]:
    m = _EMP.search(query)
    return (
        (int((m.group(1) or "0").replace(",", "")) or None, int((m.group(2) or "0").replace(",", "")) or None)
        if m
        else (None, None)
    )


def _repair(criteria: SearchCriteria, field: str, value, mismatch, label: str | None = None) -> None:
    current = getattr(criteria, field)
    if not value:
        return
    if current and mismatch(current, value):
        _conflict(criteria, f"{label or field}: llm={current} regex={value}")
    elif not current:
        setattr(criteria, field, value)


async def parse_query(query: str, llm: LLMClient) -> SearchCriteria:
    try:
        criteria = await llm.parse(SearchCriteria, _PARSE_PROMPT.format(query=query))
    except _RECOVERABLE:
        criteria = SearchCriteria()
    country = _country(query)
    region = _region(query)
    certs = _certs(query)
    mn, mx = _employees(query)
    _repair(criteria, "country", country, lambda a, b: match_country(a, b) != "VERIFIED")
    _repair(criteria, "region", region, lambda a, b: a.lower() != b.lower())
    _repair(criteria, "certifications", certs, lambda a, b: set(a) != set(b))
    _repair(criteria, "min_employees", mn, lambda a, b: a != b)
    _repair(criteria, "max_employees", mx, lambda a, b: a != b)
    criteria.raw_query = query
    return criteria
