from __future__ import annotations

import re

import pycountry

from vss.semantics import certs, same_category

_NUM = re.compile(r"[\d,]+")


def _to_alpha2(c: str | None) -> str:
    if not c:
        return ""
    c = c.strip()
    if len(c) <= 3:
        c = c.upper()
    try:
        return pycountry.countries.lookup(c).alpha_2
    except LookupError:
        pass
    try:
        return pycountry.countries.search_fuzzy(c)[0].alpha_2
    except LookupError:
        return c.lower()


def match_country(extracted: str | None, expected: str | None) -> str:
    if not extracted:
        return "UNKNOWN"
    if not expected:
        return "VERIFIED"
    return "VERIFIED" if _to_alpha2(extracted) == _to_alpha2(expected) else "CONTRADICTED"


def match_certs(extracted: str | None, expected: list[str]) -> str:
    if not extracted:
        return "UNKNOWN"
    if not expected:
        return "VERIFIED"
    found = certs(extracted)
    return "VERIFIED" if any(c in found for c in expected) else "UNKNOWN"


def match_employees(extracted: str | None, mn: int | None, mx: int | None) -> str:
    if not extracted:
        return "UNKNOWN"
    nums = _NUM.findall(extracted.replace(",", ""))
    if not nums:
        return "UNKNOWN"
    n = int(nums[0])
    if mn and n < mn:
        return "CONTRADICTED"
    if mx and n > mx:
        return "CONTRADICTED"
    return "VERIFIED"


def match_category(extracted: str | None, expected: str | None) -> str:
    if not extracted:
        return "UNKNOWN"
    if not expected:
        return "VERIFIED"
    check = same_category(extracted, expected)
    return "VERIFIED" if check is not False else "UNKNOWN"


_MATCHERS = {
    "country_region": lambda v, c: match_country(v, c.country),
    "certifications": lambda v, c: match_certs(v, c.certifications),
    "employee_count": lambda v, c: match_employees(v, c.min_employees, c.max_employees),
    "product_category": lambda v, c: match_category(v, c.product_category),
}


def verify_field(field: str, extracted_value, criteria) -> str:
    fn = _MATCHERS.get(field)
    if not fn:
        return "VERIFIED" if extracted_value else "UNKNOWN"
    return fn(str(extracted_value) if extracted_value else None, criteria)
