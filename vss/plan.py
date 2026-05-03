from __future__ import annotations

from vss.models import FieldPlan, SearchCriteria, VerificationPlan

_FIELDS: dict[str, tuple[list[str], list[str]]] = {
    "canonical_supplier_name": (
        ["gleif", "moea", "twse", "brave", "web"],
        ["{name} company profile", "{name} headquarters"],
    ),
    "country_region": (
        ["gleif", "moea", "twse", "website", "brave"],
        ["{name} headquarters location", "{name} HQ country"],
    ),
    "product_category": (
        ["twse", "website", "brave", "web"],
        ["{name} products services", "{name} what does it make"],
    ),
    "certifications": (["iaf", "website"], ["{name} ISO certification", "{name} certifications quality"]),
    "employee_count": (
        ["twse", "website", "brave", "web"],
        ["{name} number of employees", "{name} company size headcount"],
    ),
    "website": (["website", "ops", "brave", "web"], ["{name} official website"]),
}

_ALWAYS = {"canonical_supplier_name", "country_region", "product_category", "website"}


def _is_critical(field: str, criteria: SearchCriteria) -> bool:
    if field == "country_region" and criteria.country:
        return True
    if field == "certifications" and criteria.certifications:
        return True
    return field == "employee_count" and bool(criteria.min_employees or criteria.max_employees)


def plan_verification(criteria: SearchCriteria) -> VerificationPlan:
    plans = []
    for field, (sources, queries) in _FIELDS.items():
        expected = getattr(criteria, field, None) if field not in _ALWAYS else None
        if field in _ALWAYS or expected is not None or _is_critical(field, criteria):
            plans.append(
                FieldPlan(field=field, sources=sources, queries=queries, critical=_is_critical(field, criteria))
            )
    return VerificationPlan(fields=plans)
