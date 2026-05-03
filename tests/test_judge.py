from vss.judge import (
    _det,
    _supp_country,
    _supp_employee,
    _supp_name,
    _supp_product,
    _supp_website,
    _support_indices,
)
from vss.models import Evidence, ExtractedField, SearchCriteria, SourceTier
from vss.plan import plan_verification


def _ev(source, tier, **kw) -> Evidence:
    return Evidence(source=source, source_tier=tier, snippet=kw.get("snippet", ""), url=kw.get("url", ""))


def test_deterministic_judge_keeps_multiple_name_sources():
    c = SearchCriteria(product_category="semiconductors", country="Taiwan")
    plan = plan_verification(c)
    ev = [
        _ev("GLEIF", SourceTier.A, snippet="LEI: 1 | TSMC | Hsinchu, TW"),
        _ev("MOEA Taiwan", SourceTier.A, snippet="TSMC | ID: 22099131"),
        _ev("Company Website", SourceTier.B, url="https://www.tsmc.com", snippet="semiconductor manufacturing"),
    ]
    out = _det("TSMC", c, plan, ev)
    assert out["canonical_supplier_name"].supporting_indices == [0, 1]
    assert out["country_region"].supporting_indices == [0, 1]


def test_ai_category_does_not_match_taiwan_or_maintenance():
    c = SearchCriteria(product_category="AI")
    plan = plan_verification(c)
    ev = [
        _ev("GLEIF", SourceTier.A, snippet="TSMC PRODUCTION & MAINTENANCE CONSULTANTS ApS | Snekkersten, DK"),
        _ev("DuckDuckGo", SourceTier.B, snippet="TSMC is a Taiwanese multinational semiconductor manufacturer."),
    ]
    assert "product_category" not in _det("TSMC", c, plan, ev)


def test_semiconductor_category_uses_product_sources_not_gleif():
    c = SearchCriteria(product_category="semiconductors")
    plan = plan_verification(c)
    ev = [
        _ev("GLEIF", SourceTier.A, snippet="LEI: 1 | Random Semiconductor Holding | Road Town, VG"),
        _ev("DuckDuckGo", SourceTier.B, snippet="TSMC is a dedicated semiconductor foundry."),
    ]
    assert _det("TSMC", c, plan, ev)["product_category"].supporting_indices == [1]


def test_supp_employee_requires_value_within_tolerance():
    pairs = [(0, _ev("Company Website", SourceTier.B, snippet="65,000 employees"))]
    assert _supp_employee("65000", pairs, SearchCriteria()) == [0]
    assert _supp_employee("64000", pairs, SearchCriteria()) == [0]
    assert _supp_employee("100000", pairs, SearchCriteria()) == []


def test_supp_employee_rejects_unrelated_numbers():
    pairs = [(0, _ev("Brave Search", SourceTier.B, snippet="Founded in 1987 with 12 board members"))]
    assert _supp_employee("65000", pairs, SearchCriteria()) == []


def test_supp_country_requires_hq_context_for_non_registry():
    pairs = [
        (0, _ev("Brave Search", SourceTier.B, snippet="TSMC also serves customers in Vietnam.")),
        (1, _ev("Brave Search", SourceTier.B, snippet="TSMC is headquartered in Taiwan.")),
    ]
    assert _supp_country("Taiwan", pairs, SearchCriteria()) == [1]
    assert _supp_country("Vietnam", pairs, SearchCriteria()) == []


def test_supp_country_accepts_registry_mention():
    pairs = [(0, _ev("GLEIF", SourceTier.A, snippet="LEI: 1 | TSMC | Hsinchu, TW"))]
    assert _supp_country("Taiwan", pairs, SearchCriteria()) == [0]


def test_supp_website_matches_normalized_domain():
    pairs = [(0, _ev("Company Website", SourceTier.B, url="https://www.tsmc.com/path"))]
    assert _supp_website("tsmc.com", pairs, SearchCriteria()) == [0]
    assert _supp_website("umc.com", pairs, SearchCriteria()) == []


def test_supp_name_uses_token_set_ratio():
    pairs = [(0, _ev("Brave Search", SourceTier.B, snippet="Hon Hai Precision Industry Co., Ltd."))]
    assert _supp_name("Hon Hai Precision Industry", pairs, SearchCriteria()) == [0]


def test_supp_product_only_counts_product_sources():
    pairs = [
        (0, _ev("GLEIF", SourceTier.A, snippet="dedicated semiconductor foundry")),
        (1, _ev("DuckDuckGo", SourceTier.B, snippet="dedicated semiconductor foundry")),
    ]
    assert _supp_product("semiconductors", pairs, SearchCriteria()) == [1]


def test_support_indices_drops_unsupported_llm_extraction():
    snippets = [_ev("Brave Search", SourceTier.B, snippet="Founded 1987 with 12 board members")]
    e = ExtractedField(field="employee_count", value="65000", supporting_indices=[0])
    assert _support_indices(e, snippets, SearchCriteria()) == []
