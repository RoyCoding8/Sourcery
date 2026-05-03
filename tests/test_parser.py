import pytest

from vss.llm import get_llm
from vss.llm.stub import StubLLM
from vss.models import SearchCriteria
from vss.parser import parse_query
from vss.settings import has_creds, models_for


class BadParseLLM:
    async def parse(self, schema, _prompt):
        return schema.model_validate({"product_category": "AI", "country": None})


def test_get_llm_stub():
    assert isinstance(get_llm("stub"), StubLLM)


@pytest.mark.asyncio
async def test_parse_query_stub():
    criteria = await parse_query("Top 5 semiconductor manufacturers in Taiwan", get_llm("stub"))
    assert isinstance(criteria, SearchCriteria)
    assert criteria.raw_query == "Top 5 semiconductor manufacturers in Taiwan"
    assert criteria.country == "Taiwan"
    assert "semiconductor" in criteria.product_category.lower()


@pytest.mark.asyncio
async def test_parse_query_repairs_country_null():
    criteria = await parse_query("Top 5 AI companies in China", BadParseLLM())
    assert criteria.country == "China"
    assert criteria.product_category == "AI"


@pytest.mark.asyncio
async def test_parse_query_does_not_repair_negated_country():
    criteria = await parse_query("AI suppliers not in China", BadParseLLM())
    assert criteria.country == ""


@pytest.mark.asyncio
async def test_parse_query_demonym_uses_llm_semantics():
    criteria = await parse_query("Top 5 Chinese AI companies", get_llm("stub"))
    assert criteria.country == "China"
    assert criteria.product_category == "AI"


def test_models_for_empty():
    assert models_for("nonexistent") == []


def test_has_creds_stub():
    assert has_creds("stub") is True
