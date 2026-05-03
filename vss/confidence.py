from __future__ import annotations

import math
from datetime import UTC, datetime

from vss.models import Confidence, Evidence, FieldScore, JudgedField, SourceTier
from vss.normalize import normalize_domain

WEIGHT: dict[tuple[str, str], float] = {
    ("canonical_supplier_name", "GLEIF"): 1.0,
    ("canonical_supplier_name", "MOEA Taiwan"): 1.0,
    ("canonical_supplier_name", "TWSE MOPS"): 1.0,
    ("canonical_supplier_name", "IAF CertSearch"): 0.7,
    ("canonical_supplier_name", "Company Website"): 0.5,
    ("canonical_supplier_name", "Brave Search"): 0.3,
    ("canonical_supplier_name", "Tavily"): 0.3,
    ("canonical_supplier_name", "DuckDuckGo"): 0.2,
    ("country_region", "MOEA Taiwan"): 1.0,
    ("country_region", "TWSE MOPS"): 1.0,
    ("country_region", "GLEIF"): 0.95,
    ("country_region", "Domain Authority"): 0.4,
    ("country_region", "Company Website"): 0.4,
    ("country_region", "Brave Search"): 0.3,
    ("country_region", "Tavily"): 0.3,
    ("country_region", "DuckDuckGo"): 0.2,
    ("website", "Company Website"): 0.9,
    ("website", "Domain Authority"): 0.7,
    ("website", "Brave Search"): 0.4,
    ("website", "Tavily"): 0.4,
    ("website", "DuckDuckGo"): 0.3,
    ("certifications", "IAF CertSearch"): 1.0,
    ("certifications", "Company Website"): 0.5,
    ("certifications", "Brave Search"): 0.3,
    ("certifications", "Tavily"): 0.3,
    ("certifications", "DuckDuckGo"): 0.2,
    ("employee_count", "TWSE MOPS"): 0.9,
    ("employee_count", "Company Website"): 0.5,
    ("employee_count", "Brave Search"): 0.4,
    ("employee_count", "Tavily"): 0.4,
    ("employee_count", "DuckDuckGo"): 0.3,
    ("product_category", "TWSE MOPS"): 0.85,
    ("product_category", "Company Website"): 0.7,
    ("product_category", "Brave Search"): 0.4,
    ("product_category", "Tavily"): 0.4,
    ("product_category", "DuckDuckGo"): 0.3,
}
TIER_FALLBACK = {SourceTier.A: 0.5, SourceTier.B: 0.2, SourceTier.C: 0.0}
DECAY_FIELDS = {"employee_count", "certifications", "product_category"}
HIGH_THRESHOLD = 0.85
MEDIUM_THRESHOLD = 0.55
W_CAP = 0.95
CONFLICT_FLOOR = 0.5


def _key(e: Evidence) -> tuple[str, str]:
    return e.source, normalize_domain(e.url) or e.source


def _age_days(fetched_at: str) -> float:
    if not fetched_at:
        return 0.0
    try:
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return max(0.0, (datetime.now(UTC) - ts).total_seconds() / 86400)


def _decay(field: str, e: Evidence) -> float:
    if field not in DECAY_FIELDS:
        return 1.0
    return math.exp(-_age_days(e.fetched_at) / 365)


def _weight(field: str, e: Evidence) -> float:
    base = WEIGHT.get((field, e.source), TIER_FALLBACK.get(e.source_tier, 0.0))
    return min(W_CAP, base * _decay(field, e))


def _aggregate(field: str, evidence: list[Evidence]) -> tuple[float, dict[tuple[str, str], float]]:
    by_key: dict[tuple[str, str], float] = {}
    for e in evidence:
        w = _weight(field, e)
        if w <= 0:
            continue
        k = _key(e)
        if w > by_key.get(k, 0.0):
            by_key[k] = w
    p_miss = 1.0
    for w in by_key.values():
        p_miss *= 1 - w
    return 1 - p_miss, by_key


def _bucket(score: float, n_sources: int) -> Confidence:
    if n_sources >= 2 and score >= HIGH_THRESHOLD:
        return Confidence.HIGH
    if score >= MEDIUM_THRESHOLD:
        return Confidence.MEDIUM
    return Confidence.LOW


def _reason(score: float, by_key: dict[tuple[str, str], float]) -> str:
    if not by_key:
        return "No corroborating sources"
    top = sorted(by_key.items(), key=lambda kv: -kv[1])[:5]
    return f"score={score:.2f} from " + ", ".join(f"{k[0]} ({w:.2f})" for k, w in top)


def field_score(field: str, evidence: list[Evidence]) -> float:
    score, _ = _aggregate(field, evidence)
    return score


def score_field(field: str, value: object, evidence: list[Evidence]) -> FieldScore:
    score, by_key = _aggregate(field, evidence)
    return FieldScore(
        value=value,
        confidence=_bucket(score, len(by_key)),
        reason=_reason(score, by_key),
        evidence=evidence,
    )


def score_judged(j: JudgedField, snippets: list[Evidence], field_snippets: list[Evidence] | None = None) -> FieldScore:
    supporting = [snippets[i] for i in j.supporting_indices if 0 <= i < len(snippets)]
    support_keys = {(*_key(e), e.snippet) for e in supporting}
    conflicts = [
        e
        for e in (field_snippets or snippets)
        if (*_key(e), e.snippet) not in support_keys and _weight(j.field, e) >= 0.3
    ]
    if j.status == "CONTRADICTED":
        return FieldScore(
            value=j.value,
            confidence=Confidence.LOW,
            reason=f"CONTRADICTED: {j.reason}",
            evidence=supporting,
            conflicts=conflicts,
        )
    if j.status != "VERIFIED" or not supporting:
        return FieldScore(
            value=j.value,
            confidence=Confidence.LOW,
            reason=f"{j.status}: {j.reason or 'no supporting evidence'}",
            evidence=supporting,
            conflicts=conflicts,
        )
    score, by_key = _aggregate(j.field, supporting)
    bucket = _bucket(score, len(by_key))
    capped = ""
    if bucket == Confidence.HIGH and any(_weight(j.field, e) >= CONFLICT_FLOOR for e in conflicts):
        bucket = Confidence.MEDIUM
        capped = " | capped to MEDIUM by conflicting evidence"
    return FieldScore(
        value=j.value,
        confidence=bucket,
        reason=f"{j.status}: {j.reason} | {_reason(score, by_key)}{capped}",
        evidence=supporting,
        conflicts=conflicts,
    )
