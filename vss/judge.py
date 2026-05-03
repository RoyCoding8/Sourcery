from __future__ import annotations

import re

import pycountry
from rapidfuzz import fuzz

from vss.llm import LLMClient
from vss.models import Evidence, ExtractedField, ExtractedFields, SearchCriteria, VerificationPlan
from vss.normalize import normalize_domain, normalize_name
from vss.semantics import certs, has_category

_PROMPT = """Extract factual values for each field from the snippets below.

Company: {name}
Declared HQ: {country}

Fields to extract:
{fields}

Snippets (numbered):
{snippets}

For each field return:
- field: the field name
- value: the factual value found in snippets (null if not found)
- supporting_indices: which snippet numbers support this value

Rules:
- Only extract values explicitly stated in snippets. Do NOT infer or guess.
- Mere mention of a company name is NOT evidence for any field except canonical_supplier_name.
- For employee_count: only extract if the snippet contains an actual number with context like "employees" or "staff".
- For country_region: extract the HQ/headquarters country, not countries where they operate or sell."""

_EMP_PHRASE = re.compile(r"\b([\d,]+)\s*\+?\s*(?:employees|staff|people|workers|headcount)\b", re.I)
_HQ_TERM = re.compile(
    r"(?:headquarter|hq|based\s+in|located\s+in|registered\s+in|head\s+office|incorporated\s+in)", re.I
)
_COUNTRY_SOURCES = {"Taiwan": {"MOEA Taiwan", "TWSE MOPS"}}
_PRODUCT_SOURCES = {"Company Website", "Brave Search", "Tavily", "DuckDuckGo"}
_REGISTRY_SOURCES = {"GLEIF", "MOEA Taiwan", "TWSE MOPS", "Domain Authority"}
_NAME_FUZZ = 85
_EMP_TOLERANCE = 0.10


def _has_country(text: str, country: str) -> bool:
    try:
        iso = pycountry.countries.lookup(country).alpha_2
    except LookupError:
        iso = ""
    return country.lower() in text.lower() or bool(iso and re.search(rf"\b{iso}\b", text, re.I))


def _iso(country: str) -> str:
    try:
        return pycountry.countries.lookup(country).alpha_2
    except LookupError:
        return ""


def _gleif_country(s: Evidence, country: str) -> bool:
    m = re.search(r",\s*([A-Z]{2})\s*$", s.snippet)
    return s.source == "GLEIF" and bool(m and m.group(1) == _iso(country))


def _mentions_name(name: str, text: str) -> bool:
    n, t = normalize_name(name), normalize_name(text)
    if not n or not t:
        return False
    if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", t):
        return True
    return fuzz.token_set_ratio(n, t) >= _NAME_FUZZ


def _to_int(v: object) -> int | None:
    nums = re.findall(r"\d[\d,]*", str(v))
    return int(nums[0].replace(",", "")) if nums else None


def _terms(v: object) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]{3,}", str(v).lower())]


def _det(
    name: str, criteria: SearchCriteria, plan: VerificationPlan, snippets: list[Evidence]
) -> dict[str, ExtractedField]:
    out: dict[str, ExtractedField] = {}
    for fp in plan.fields:
        hits = [(i, s) for i, s in enumerate(snippets) if s.snippet]
        if fp.field == "canonical_supplier_name":
            idx = [i for i, s in hits if _mentions_name(name, s.snippet)]
            if idx:
                out[fp.field] = ExtractedField(field=fp.field, value=name, supporting_indices=idx)
        elif fp.field == "website":
            url_hits = [(i, s) for i, s in enumerate(snippets) if s.source == "Company Website" and s.url]
            if url_hits:
                out[fp.field] = ExtractedField(
                    field=fp.field, value=url_hits[0][1].url, supporting_indices=[i for i, _ in url_hits]
                )
        elif fp.field == "country_region" and criteria.country:
            local = _COUNTRY_SOURCES.get(criteria.country, set())
            idx = [i for i, s in hits if s.source in local or _gleif_country(s, criteria.country)]
            if idx:
                out[fp.field] = ExtractedField(field=fp.field, value=criteria.country, supporting_indices=idx)
        elif fp.field == "product_category" and criteria.product_category:
            idx = [
                i
                for i, s in hits
                if s.source in _PRODUCT_SOURCES and has_category(s.snippet, criteria.product_category) is True
            ]
            if idx:
                out[fp.field] = ExtractedField(field=fp.field, value=criteria.product_category, supporting_indices=idx)
        elif fp.field == "certifications" and criteria.certifications:
            idx = [i for i, s in hits if any(c in certs(s.snippet) for c in criteria.certifications)]
            if idx:
                out[fp.field] = ExtractedField(
                    field=fp.field, value=", ".join(criteria.certifications), supporting_indices=idx
                )
        elif fp.field == "employee_count":
            for i, s in hits:
                if m := _EMP_PHRASE.search(s.snippet):
                    out[fp.field] = ExtractedField(field=fp.field, value=m.group(0), supporting_indices=[i])
                    break
    return out


def _supp_website(value: object, pairs: list[tuple[int, Evidence]], _c: SearchCriteria) -> list[int]:
    target = normalize_domain(str(value))
    if not target:
        return []
    return [i for i, s in pairs if normalize_domain(s.url) == target]


def _supp_name(value: object, pairs: list[tuple[int, Evidence]], _c: SearchCriteria) -> list[int]:
    return [i for i, s in pairs if _mentions_name(str(value), s.snippet)]


def _supp_country(value: object, pairs: list[tuple[int, Evidence]], _c: SearchCriteria) -> list[int]:
    val = str(value)
    out = []
    for i, s in pairs:
        text = f"{s.snippet} {s.url}"
        if not _has_country(text, val):
            continue
        if s.source in _REGISTRY_SOURCES or s.source == "Company Website" or _HQ_TERM.search(text):
            out.append(i)
    return out


def _supp_employee(value: object, pairs: list[tuple[int, Evidence]], _c: SearchCriteria) -> list[int]:
    target = _to_int(value)
    out = []
    for i, s in pairs:
        for m in _EMP_PHRASE.finditer(s.snippet):
            n = _to_int(m.group(1))
            if n is None:
                continue
            if target is None or (target > 0 and abs(n - target) / target <= _EMP_TOLERANCE):
                out.append(i)
                break
    return out


def _supp_product(value: object, pairs: list[tuple[int, Evidence]], _c: SearchCriteria) -> list[int]:
    val = str(value)
    out = []
    for i, s in pairs:
        if s.source not in _PRODUCT_SOURCES:
            continue
        check = has_category(s.snippet, val)
        if check is True:
            out.append(i)
            continue
        if check is None and any(t in s.snippet.lower() for t in _terms(val)):
            out.append(i)
    return out


def _supp_certifications(_value: object, pairs: list[tuple[int, Evidence]], criteria: SearchCriteria) -> list[int]:
    expected = set(criteria.certifications) if criteria.certifications else None
    out = []
    for i, s in pairs:
        found = certs(s.snippet)
        if (expected and any(c in found for c in expected)) or (not expected and found):
            out.append(i)
    return out


def _supp_default(value: object, pairs: list[tuple[int, Evidence]], _c: SearchCriteria) -> list[int]:
    terms = _terms(value)
    if not terms:
        return [i for i, _ in pairs]
    return [i for i, s in pairs if any(t in (s.snippet + " " + s.url).lower() for t in terms)]


_SUPPORT = {
    "canonical_supplier_name": _supp_name,
    "website": _supp_website,
    "country_region": _supp_country,
    "employee_count": _supp_employee,
    "product_category": _supp_product,
    "certifications": _supp_certifications,
}


def _support_indices(e: ExtractedField, snippets: list[Evidence], criteria: SearchCriteria) -> list[int]:
    if e.value in (None, ""):
        return []
    pairs = [(i, snippets[i]) for i in e.supporting_indices if 0 <= i < len(snippets)]
    if not pairs:
        return []
    return _SUPPORT.get(e.field, _supp_default)(e.value, pairs, criteria)


async def extract_fields(
    name: str,
    country: str | None,
    criteria: SearchCriteria,
    plan: VerificationPlan,
    snippets: list[Evidence],
    llm: LLMClient,
) -> list[ExtractedField]:
    found = _det(name, criteria, plan, snippets)
    missing = [fp for fp in plan.fields if fp.field not in found]
    if not missing or not snippets:
        return [found.get(fp.field, ExtractedField(field=fp.field)) for fp in plan.fields]
    fields_text = "\n".join(f"- {fp.field}" for fp in missing)
    blob = "\n".join(
        f"[{i}] ({s.source} / Tier-{s.source_tier.value}) URL: {s.url}\n    Snippet: {s.snippet[:300]}"
        for i, s in enumerate(snippets)
    )
    res = await llm.parse(
        ExtractedFields,
        _PROMPT.format(name=name, country=country or "unspecified", fields=fields_text, snippets=blob),
    )
    by_field = dict(found)
    for ext in res.fields:
        if ext.field in by_field:
            continue
        proving = _support_indices(ext, snippets, criteria)
        if proving:
            by_field[ext.field] = ExtractedField(field=ext.field, value=ext.value, supporting_indices=proving)
    return [by_field.get(fp.field, ExtractedField(field=fp.field)) for fp in plan.fields]
