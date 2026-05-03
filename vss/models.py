from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _list(v: Any) -> list[str]:
    return [] if v is None else ([str(v)] if isinstance(v, str) else v)


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SourceTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class SearchCriteria(BaseModel):
    product_category: str = Field(
        default="", description="The core product or service category, e.g. 'semiconductors' or 'AI'"
    )
    region: str = Field(default="", description="Geographic region if mentioned, e.g. 'Southeast Asia'")
    country: str = Field(
        default="", description="Specific country name if mentioned in the query, e.g. 'China', 'Taiwan', 'US'"
    )
    certifications: list[str] = Field(default_factory=list)
    min_employees: int | None = None
    max_employees: int | None = None
    additional_filters: dict[str, str] = Field(default_factory=dict)
    raw_query: str = ""

    clean_strings = field_validator("product_category", "region", "country", "raw_query", mode="before")(_str)
    clean_certifications = field_validator("certifications", mode="before")(_list)

    @field_validator("additional_filters", mode="before")
    @classmethod
    def _dict(cls, v: Any) -> dict[str, str]:
        return {} if v is None else v


class Evidence(BaseModel):
    source: str
    source_tier: SourceTier
    url: str = ""
    fetched_at: str = ""
    snippet: str = ""


class FieldScore(BaseModel):
    value: Any = None
    confidence: Confidence = Confidence.LOW
    reason: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    conflicts: list[Evidence] = Field(default_factory=list)


class SupplierRecord(BaseModel):
    canonical_supplier_name: FieldScore = Field(default_factory=FieldScore)
    website: FieldScore = Field(default_factory=FieldScore)
    country_region: FieldScore = Field(default_factory=FieldScore)
    product_category: FieldScore = Field(default_factory=FieldScore)
    certifications: FieldScore = Field(default_factory=FieldScore)
    employee_count: FieldScore = Field(default_factory=FieldScore)
    notes: str = ""


class SupplierList(BaseModel):
    query: str
    criteria: SearchCriteria
    suppliers: list[SupplierRecord] = Field(default_factory=list)
    partial: bool = False


class CandidateHypothesis(BaseModel):
    name: str = ""
    website: str | None = None
    country: str | None = None
    reason: str = ""

    clean_values = field_validator("name", "website", "country", "reason", mode="before")(
        lambda v: None if v is None else str(v)
    )


class CandidateList(BaseModel):
    candidates: list[CandidateHypothesis] = Field(default_factory=list)


class FieldPlan(BaseModel):
    field: str
    queries: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    critical: bool = False


class VerificationPlan(BaseModel):
    fields: list[FieldPlan] = Field(default_factory=list)


class JudgedField(BaseModel):
    field: str = ""
    value: Any = None
    status: str = "UNKNOWN"
    reason: str = ""
    supporting_indices: list[int] = Field(default_factory=list)


class JudgedFieldList(BaseModel):
    fields: list[JudgedField] = Field(default_factory=list)


class LocaleQueries(BaseModel):
    queries: list[str] = Field(default_factory=list)

    clean_queries = field_validator("queries", mode="before")(_list)


class SearchQueries(BaseModel):
    queries: list[str] = Field(default_factory=list)

    clean_queries = field_validator("queries", mode="before")(_list)


class ExtractedField(BaseModel):
    field: str = ""
    value: Any = None
    supporting_indices: list[int] = Field(default_factory=list)

    clean_field = field_validator("field", mode="before")(_str)
    clean_indices = field_validator("supporting_indices", mode="before")(lambda v: [] if v is None else v)


class ExtractedFields(BaseModel):
    fields: list[ExtractedField] = Field(default_factory=list)
