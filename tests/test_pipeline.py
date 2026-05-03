import pytest

from vss.pipeline import run


@pytest.mark.asyncio
async def test_stub_pipeline_returns_suppliers():
    result = await run("Top 5 semiconductor manufacturers in Taiwan", provider="stub")
    assert len(result.suppliers) <= 5
    assert result.query == "Top 5 semiconductor manufacturers in Taiwan"
    for s in result.suppliers:
        assert s.canonical_supplier_name.value is not None
        assert s.canonical_supplier_name.confidence in ("HIGH", "MEDIUM", "LOW")
        assert len(s.canonical_supplier_name.evidence) > 0


@pytest.mark.asyncio
async def test_stub_pipeline_has_criteria():
    result = await run("Top 5 semiconductor manufacturers in Taiwan", provider="stub")
    assert result.criteria.country == "Taiwan"
    assert "semiconductor" in result.criteria.product_category.lower()
