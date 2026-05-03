import pytest

import vss.candidates as cm
from vss.candidates import _valid, generate_candidates
from vss.llm.stub import StubLLM
from vss.models import CandidateHypothesis, SearchCriteria


@pytest.fixture
def no_seed(monkeypatch):
    async def empty(_):
        return []

    monkeypatch.setattr(cm, "_gleif_seed", empty)


@pytest.mark.asyncio
async def test_china_ai_uses_country_seed(_no_seed):
    c = SearchCriteria(product_category="AI", country="China")
    names = [x.name for x in await generate_candidates(c, StubLLM())]
    assert names[:2] == ["Baidu Inc.", "Alibaba Cloud"]
    assert all(x.country == "China" for x in await generate_candidates(c, StubLLM()))


def test_country_constrained_candidate_requires_country():
    c = SearchCriteria(product_category="AI", country="China")
    assert not _valid(CandidateHypothesis(name="Example AI", website="https://example.com"), c)
    assert not _valid(CandidateHypothesis(name="Example AI", website="https://example.com", country="Japan"), c)
