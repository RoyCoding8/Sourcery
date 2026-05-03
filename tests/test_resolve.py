from vss.models import CandidateHypothesis
from vss.normalize import normalize_name
from vss.resolve import resolve_entities


def test_foxconn_merge_by_domain():
    result = resolve_entities(
        [
            CandidateHypothesis(name="Foxconn", website="https://www.foxconn.com", country="Taiwan"),
            CandidateHypothesis(
                name="Hon Hai Precision Industry Co., Ltd.", website="https://www.foxconn.com", country="Taiwan"
            ),
        ]
    )
    assert len(result) == 1
    assert "foxconn.com" in (result[0].website or "")


def test_no_false_merge():
    result = resolve_entities(
        [
            CandidateHypothesis(name="TSMC", website="https://www.tsmc.com"),
            CandidateHypothesis(name="MediaTek", website="https://www.mediatek.com"),
        ]
    )
    assert len(result) == 2


def test_cjk_normalize():
    assert "hong" in normalize_name("鴻海精密工業")


def test_cleanco_strip():
    assert "tsmc" in normalize_name("TSMC Co., Ltd.")
