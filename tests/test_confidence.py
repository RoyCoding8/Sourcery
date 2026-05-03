from datetime import UTC, datetime, timedelta

from vss.confidence import field_score, score_field, score_judged
from vss.models import Confidence, Evidence, JudgedField, SourceTier


def _ev(source: str, tier: SourceTier, **kw) -> Evidence:
    return Evidence(
        source=source,
        source_tier=tier,
        snippet=kw.get("snippet", "x"),
        url=kw.get("url", ""),
        fetched_at=kw.get("fetched_at", ""),
    )


def test_two_authoritative_sources_high():
    r = score_field(
        "canonical_supplier_name",
        "TSMC",
        [_ev("GLEIF", SourceTier.A), _ev("MOEA Taiwan", SourceTier.A)],
    )
    assert r.confidence == Confidence.HIGH


def test_authoritative_plus_corroboration_high():
    r = score_field(
        "canonical_supplier_name",
        "TSMC",
        [_ev("GLEIF", SourceTier.A), _ev("Company Website", SourceTier.B, url="https://tsmc.com")],
    )
    assert r.confidence == Confidence.HIGH


def test_single_authoritative_caps_at_medium():
    r = score_field("canonical_supplier_name", "TSMC", [_ev("GLEIF", SourceTier.A)])
    assert r.confidence == Confidence.MEDIUM


def test_two_weak_sources_medium():
    r = score_field(
        "product_category",
        "semiconductors",
        [_ev("Brave Search", SourceTier.B), _ev("DuckDuckGo", SourceTier.B)],
    )
    assert r.confidence == Confidence.MEDIUM


def test_single_weak_source_low():
    r = score_field("product_category", "semiconductors", [_ev("Brave Search", SourceTier.B)])
    assert r.confidence == Confidence.LOW


def test_tier_c_only_is_low():
    r = score_field("canonical_supplier_name", "TSMC", [_ev("LLM hypothesis", SourceTier.C)])
    assert r.confidence == Confidence.LOW


def test_no_evidence_is_low():
    assert score_field("canonical_supplier_name", None, []).confidence == Confidence.LOW


def test_per_field_weights_diverge_for_same_source():
    name_score = field_score(
        "canonical_supplier_name",
        [_ev("GLEIF", SourceTier.A), _ev("Company Website", SourceTier.B, url="https://x.com")],
    )
    emp_score = field_score(
        "employee_count",
        [_ev("GLEIF", SourceTier.A), _ev("Company Website", SourceTier.B)],
    )
    assert name_score > emp_score


def test_recency_decay_lowers_old_employee_evidence():
    fresh = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    old = (datetime.now(UTC) - timedelta(days=730)).isoformat()
    fresh_score = field_score("employee_count", [_ev("Company Website", SourceTier.B, fetched_at=fresh)])
    old_score = field_score("employee_count", [_ev("Company Website", SourceTier.B, fetched_at=old)])
    assert fresh_score > old_score


def test_no_decay_for_stable_field():
    fresh = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    old = (datetime.now(UTC) - timedelta(days=2000)).isoformat()
    a = field_score("canonical_supplier_name", [_ev("GLEIF", SourceTier.A, fetched_at=fresh)])
    b = field_score("canonical_supplier_name", [_ev("GLEIF", SourceTier.A, fetched_at=old)])
    assert a == b


def test_conflict_caps_high_to_medium():
    snippets = [
        _ev("GLEIF", SourceTier.A, snippet="LEI: 1 | TSMC | Hsinchu, TW"),
        _ev("MOEA Taiwan", SourceTier.A, snippet="TSMC | ID: 22099131"),
        _ev("TWSE MOPS", SourceTier.A, snippet="2330 | Vietnam"),
    ]
    j = JudgedField(field="country_region", value="Taiwan", status="VERIFIED", reason="ok", supporting_indices=[0, 1])
    fs = score_judged(j, snippets)
    assert fs.confidence == Confidence.MEDIUM
    assert "capped to MEDIUM" in fs.reason


def test_contradicted_status_is_low():
    j = JudgedField(
        field="country_region", value="Taiwan", status="CONTRADICTED", reason="says Vietnam", supporting_indices=[]
    )
    assert score_judged(j, []).confidence == Confidence.LOW


def test_unknown_status_is_low():
    j = JudgedField(field="employee_count", value=None, status="UNKNOWN", reason="not found", supporting_indices=[])
    assert score_judged(j, []).confidence == Confidence.LOW


def test_unrecognized_source_falls_back_to_low():
    a = score_field("canonical_supplier_name", "X", [_ev("Made-up Source", SourceTier.A)])
    c = score_field("canonical_supplier_name", "X", [_ev("Random Site", SourceTier.C)])
    assert a.confidence == Confidence.LOW
    assert c.confidence == Confidence.LOW
