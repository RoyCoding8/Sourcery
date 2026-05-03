from vss.models import SearchCriteria
from vss.verify import match_category, match_certs, match_country, match_employees, verify_field


def _criteria(**kw) -> SearchCriteria:
    return SearchCriteria(
        product_category=kw.get("product_category", "test"), **{k: v for k, v in kw.items() if k != "product_category"}
    )


def test_country_china_cn():
    assert match_country("CN", "China") == "VERIFIED"
    assert match_country("China", "china") == "VERIFIED"


def test_country_mismatch():
    assert match_country("United States", "China") == "CONTRADICTED"


def test_country_none():
    assert match_country(None, "China") == "UNKNOWN"
    assert match_country("China", None) == "VERIFIED"


def test_certs_found():
    assert match_certs("ISO 9001:2015 Quality Management", ["ISO 9001"]) == "VERIFIED"


def test_certs_missing():
    assert match_certs("CE marking", ["ISO 9001"]) == "UNKNOWN"


def test_certs_none():
    assert match_certs(None, ["ISO 9001"]) == "UNKNOWN"


def test_employees_in_range():
    assert match_employees("5000 employees", 100, 10000) == "VERIFIED"


def test_employees_too_few():
    assert match_employees("50 staff", 100, None) == "CONTRADICTED"


def test_employees_too_many():
    assert match_employees("50000 employees", None, 200) == "CONTRADICTED"


def test_employees_none():
    assert match_employees(None, 100, 200) == "UNKNOWN"


def test_category_match():
    assert match_category("semiconductor manufacturing", "semiconductors") == "VERIFIED"


def test_category_unrelated():
    assert match_category("food processing", "semiconductors") == "UNKNOWN"


def test_verify_field_country():
    c = _criteria(country="Taiwan")
    assert verify_field("country_region", "Taiwan", c) == "VERIFIED"
    assert verify_field("country_region", "China", c) == "CONTRADICTED"


def test_verify_field_unknown_field():
    c = _criteria()
    assert verify_field("canonical_supplier_name", "TSMC", c) == "VERIFIED"
    assert verify_field("canonical_supplier_name", None, c) == "UNKNOWN"
