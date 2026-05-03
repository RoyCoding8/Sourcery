from __future__ import annotations

from vss.models import CandidateHypothesis
from vss.normalize import normalize_domain, normalize_name
from vss.verify import match_country


def _should_merge(a: CandidateHypothesis, b: CandidateHypothesis, na: str, nb: str) -> bool:
    da, db = normalize_domain(a.website), normalize_domain(b.website)
    if da and db and da == db:
        return True
    return bool(na and na == nb and a.country and b.country and match_country(a.country, b.country) == "VERIFIED")


def _merge(a: CandidateHypothesis, b: CandidateHypothesis) -> CandidateHypothesis:
    return CandidateHypothesis(
        name=a.name if len(a.name) >= len(b.name) else b.name,
        website=a.website or b.website,
        country=a.country or b.country,
        reason="; ".join(filter(None, [a.reason, b.reason])),
    )


def resolve_entities(candidates: list[CandidateHypothesis]) -> list[CandidateHypothesis]:
    merged: list[tuple[CandidateHypothesis, str]] = []
    for cand in candidates:
        norm = normalize_name(cand.name)
        found = False
        for i, (existing, existing_norm) in enumerate(merged):
            if _should_merge(cand, existing, norm, existing_norm):
                m = _merge(existing, cand)
                merged[i] = (m, normalize_name(m.name))
                found = True
                break
        if not found:
            merged.append((cand, norm))
    return [c for c, _ in merged]
