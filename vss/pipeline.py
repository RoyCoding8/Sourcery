from __future__ import annotations

import asyncio
import logging
import re

import httpx
import pycountry

from vss.candidates import MAX_CANDIDATES, generate_candidates
from vss.confidence import MEDIUM_THRESHOLD, field_score, score_field, score_judged
from vss.judge import extract_fields
from vss.llm import get_llm
from vss.models import Evidence, FieldScore, JudgedField, SourceTier, SupplierList, SupplierRecord
from vss.parser import parse_query
from vss.plan import plan_verification
from vss.resolve import resolve_entities
from vss.settings import default_provider, tool_model
from vss.sources import REGISTRY, gather, sanctions
from vss.verify import match_country, verify_field

ENTITY_SRC = {"gleif", "moea", "twse", "iaf"}
SITE_SRC = {"website", "ops"}
QUERY_SRC = {"brave", "web"}

log = logging.getLogger(__name__)
_PAREN = re.compile(r"\s*\(([^)]+)\)\s*$")
_RECOVERABLE = (httpx.HTTPError, ValueError, RuntimeError, TimeoutError)


def _strip_country_paren(name: str) -> str:
    def repl(m: re.Match[str]) -> str:
        inner = m.group(1).strip()
        try:
            pycountry.countries.lookup(inner)
            return " "
        except LookupError:
            return m.group(0)

    return _PAREN.sub(repl, name).strip() or name


def _country_match(a: str | None, b: str | None) -> bool:
    if not b:
        return True
    return bool(a and match_country(a, b) == "VERIFIED")


def _candidate_ev(name: str, reason: str = "") -> list[Evidence]:
    return [
        Evidence(source="Candidate generator", source_tier=SourceTier.C, snippet=f"{reason or 'candidate'}: {name}")
    ]


def _dedupe(snippet_groups: list[list[Evidence]]) -> list[Evidence]:
    seen = set()
    return [
        s
        for snips in snippet_groups
        for s in snips
        if (k := (s.source, s.url, s.snippet[:80])) not in seen and not seen.add(k)
    ]


async def _pass1(name, country, url, plan):
    srcs = sorted({s for fp in plan.fields for s in fp.sources if s in ENTITY_SRC | SITE_SRC})
    res = await asyncio.gather(*[REGISTRY[s](name, country, "", url) for s in srcs], return_exceptions=True)
    return [x for r in res if isinstance(r, list) for x in r]


async def _pass2(name, country, url, plan, needy):
    if not needy:
        return [[] for _ in plan.fields]
    tasks = [
        gather(name, country, url, plan.fields[k].queries, [s for s in plan.fields[k].sources if s in QUERY_SRC])
        for k in needy
    ]
    out = [[] for _ in plan.fields]
    for k, ev in zip(needy, await asyncio.gather(*tasks), strict=True):
        out[k] = ev
    return out


async def _verify(cand, criteria, plan, llm):
    name = _strip_country_paren(cand.name)
    search_country = criteria.country or cand.country
    p1 = await _pass1(name, search_country, cand.website, plan)
    needy = [k for k, fp in enumerate(plan.fields) if field_score(fp.field, p1) < MEDIUM_THRESHOLD]
    p2 = await _pass2(name, search_country, cand.website, plan, needy)
    snippets_per_field = [p1 + p2[k] for k in range(len(plan.fields))]
    flat = _dedupe(snippets_per_field)
    extracted = await extract_fields(name, search_country, criteria, plan, flat, llm)
    judged: list[JudgedField] = []
    for fp, ext in zip(plan.fields, extracted, strict=True):
        val = ext.value
        supp = [i for i in ext.supporting_indices if 0 <= i < len(flat)]
        fallback = {
            "canonical_supplier_name": (name, "no evidence cited"),
            "website": (cand.website, "from candidate, no evidence cited"),
            "country_region": (cand.country, "from candidate, no evidence cited"),
        }.get(fp.field, (None, ""))
        if not val and fallback[0]:
            val, status, reason = fallback[0], "UNKNOWN", fallback[1]
        elif not val:
            val, status, reason = None, "UNKNOWN", "not found in evidence"
        elif not supp:
            status, reason = "UNKNOWN", "extracted but unsupported"
        else:
            constraint = verify_field(fp.field, val, criteria)
            status = "CONTRADICTED" if constraint == "CONTRADICTED" else "VERIFIED"
            reason = f"supported by {len(supp)} snippet(s)" if status == "VERIFIED" else f"contradicts criteria: {val}"
        judged.append(JudgedField(field=fp.field, value=val, status=status, reason=reason, supporting_indices=supp))
    country = next((j.value for j in judged if j.field == "country_region" and j.status == "VERIFIED"), cand.country)
    sanc = await sanctions.lookup(name, country)
    return name, country, flat, snippets_per_field, judged, sanc


def _build_record(name, url, country, reason, plan, judged, snippets, snippets_per_field, sanc) -> SupplierRecord:
    rec = SupplierRecord()
    rec.canonical_supplier_name = score_field("canonical_supplier_name", name, _candidate_ev(name, reason))
    rec.country_region = (
        score_field("country_region", country, _candidate_ev(name, reason)) if country else FieldScore()
    )
    rec.website = score_field("website", url, _candidate_ev(name, reason)) if url else FieldScore()
    notes: list[str] = []
    for k, (fp, j) in enumerate(zip(plan.fields, judged, strict=True)):
        if not hasattr(rec, fp.field):
            continue
        fs = score_judged(j, snippets, snippets_per_field[k])
        if fs.evidence:
            setattr(rec, fp.field, fs)
        if j.status == "CONTRADICTED":
            notes.append(f"{fp.field} contradicted: {j.reason}")
        elif fs.conflicts:
            notes.append(f"conflict on {fp.field} ({len(fs.conflicts)} conflicting sources)")
        elif fs.confidence == "LOW" and fs.evidence:
            notes.append(f"thin data on {fp.field}")
    if sanc:
        notes.append("SANCTIONS HIT - review required")
    rec.notes = " | ".join(notes)
    return rec


async def _verify_guarded(cand, criteria, plan, llm, sem):
    async with sem:
        try:
            return await _verify(cand, criteria, plan, llm)
        except _RECOVERABLE as e:
            log.warning("verify %s failed: %s", cand.name, e)
            return None


async def run(query: str, provider: str | None = None, model: str | None = None) -> SupplierList:
    prov = provider or default_provider()
    llm = get_llm(prov, model)
    tm = tool_model(prov)
    parser_llm = get_llm(prov, tm) if tm and tm != llm.model else llm
    if tm and tm != llm.model:
        log.info("using %s for structured parsing, %s for semantic tasks", tm, llm.model)
    criteria = await parse_query(query, parser_llm)
    plan = plan_verification(criteria)
    raw = await generate_candidates(criteria, llm)
    filtered = [c for c in raw if _country_match(c.country, criteria.country)]
    candidates = resolve_entities(filtered)
    records: list[SupplierRecord] = []
    sem = asyncio.Semaphore(5)
    verify_candidates = candidates[: MAX_CANDIDATES * 2]
    results = await asyncio.gather(*[_verify_guarded(c, criteria, plan, llm, sem) for c in verify_candidates])
    for cand, result in zip(verify_candidates, results, strict=True):
        if len(records) >= MAX_CANDIDATES:
            break
        if result is None:
            continue
        name, country, flat, snippets_per_field, judged, sanc = result
        if any(fp.critical and j.status != "VERIFIED" for fp, j in zip(plan.fields, judged, strict=True)):
            continue
        records.append(
            _build_record(name, cand.website, country, cand.reason, plan, judged, flat, snippets_per_field, sanc)
        )
    return SupplierList(query=query, criteria=criteria, suppliers=records, partial=len(records) < MAX_CANDIDATES)
