from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import BaseModel

from vss.models import (
    CandidateHypothesis,
    CandidateList,
    ExtractedField,
    ExtractedFields,
    LocaleQueries,
    SearchCriteria,
    SearchQueries,
)

_TAIWAN_SEMI = [
    ("Taiwan Semiconductor Manufacturing Company", "https://www.tsmc.com", "Taiwan"),
    ("United Microelectronics Corporation", "https://www.umc.com", "Taiwan"),
    ("MediaTek Inc.", "https://www.mediatek.com", "Taiwan"),
    ("ASE Technology Holding Co., Ltd.", "https://www.aseglobal.com", "Taiwan"),
    ("Nanya Technology Corporation", "https://www.nanya.com", "Taiwan"),
]
_CHINA_AI = [
    ("Baidu Inc.", "https://www.baidu.com", "China"),
    ("Alibaba Cloud", "https://www.alibabacloud.com", "China"),
    ("Tencent Holdings Limited", "https://www.tencent.com", "China"),
    ("Huawei Technologies Co., Ltd.", "https://www.huawei.com", "China"),
    ("SenseTime Group Inc.", "https://www.sensetime.com", "China"),
]

_RESPONSES: dict[str, Any] = {
    "SearchCriteria": SearchCriteria(
        product_category="semiconductors",
        region="East Asia",
        country="Taiwan",
        raw_query="Top 5 semiconductor manufacturers in Taiwan",
    ),
    "CandidateList": CandidateList(
        candidates=[CandidateHypothesis(name=n, website=u, country=c) for n, u, c in _TAIWAN_SEMI],
    ),
    "LocaleQueries": LocaleQueries(queries=["台灣半導體製造商", "台灣晶片公司排名", "台灣半導體企業"]),
    "ExtractedFields": ExtractedFields(
        fields=[
            ExtractedField(field="canonical_supplier_name", value="Taiwan Semiconductor Manufacturing Company"),
            ExtractedField(field="country_region", value="Taiwan"),
            ExtractedField(field="product_category", value="semiconductors"),
            ExtractedField(field="website", value="https://www.tsmc.com"),
        ]
    ),
    "SearchQueries": SearchQueries(
        queries=[
            "top Taiwan semiconductor manufacturers",
            "Taiwan semiconductor company list",
            "TSMC UMC MediaTek headquarters",
            "leading Taiwan chip foundry",
        ]
    ),
}


def _idx(prompt: str, *terms: str) -> list[int]:
    return [
        int(i)
        for i, b in re.findall(r"\[(\d+)\]([\s\S]*?)(?=\n\[\d+\]|\Z)", prompt)
        if any(
            t and (re.search(rf"\b{re.escape(t.lower())}\b", b.lower()) if len(t) <= 3 else t.lower() in b.lower())
            for t in terms
        )
    ]


def _fields(prompt: str) -> ExtractedFields:
    company = (re.search(r"Company:\s*(.+)", prompt) or ["", ""])[1].strip()
    country = (re.search(r"Declared HQ:\s*(.+)", prompt) or ["", ""])[1].strip()
    wanted = set(re.findall(r"- ([a-z_]+)", prompt))
    out = []
    if "canonical_supplier_name" in wanted:
        out.append(
            ExtractedField(field="canonical_supplier_name", value=company, supporting_indices=_idx(prompt, company))
        )
    if "country_region" in wanted and country != "unspecified":
        out.append(ExtractedField(field="country_region", value=country, supporting_indices=_idx(prompt, country)))
    if "website" in wanted and (m := re.search(r"\[(\d+)\].*?URL:\s*(https?://\S+)", prompt, re.S)):
        out.append(ExtractedField(field="website", value=m.group(2), supporting_indices=[int(m.group(1))]))
    if "product_category" in wanted:
        val = (
            "AI"
            if re.search(r"\b(ai|artificial intelligence|machine learning|llm)\b", prompt, re.I)
            else "semiconductors"
            if re.search(r"\b(semiconductor|foundry|wafer|chip)\b", prompt, re.I)
            else None
        )
        if val:
            out.append(
                ExtractedField(
                    field="product_category",
                    value=val,
                    supporting_indices=_idx(
                        prompt,
                        val,
                        "artificial intelligence",
                        "machine learning",
                        "semiconductor",
                        "foundry",
                        "wafer",
                        "chip",
                    ),
                )
            )
    return ExtractedFields(fields=out)


class StubLLM:
    name: str = "stub"

    def __init__(self, model: str = "stub-v1") -> None:
        self.model = model

    async def parse(self, schema: type[BaseModel], _prompt: str) -> BaseModel:
        p = _prompt.lower()
        q = re.search(r"query:\s*(.+)", _prompt, re.I)
        target = re.search(r"for:\s*(.+?)\.\n", _prompt, re.I)
        qp = (q or target).group(1).lower() if q or target else p
        if schema.__name__ == "SearchCriteria" and ("china" in qp or "chinese" in qp) and "ai" in qp:
            return schema.model_validate(
                SearchCriteria(product_category="AI", country="China", raw_query="Top 5 AI companies in China")
            )
        if schema.__name__ == "CandidateList" and ("china" in qp or "chinese" in qp) and "ai" in qp:
            return schema.model_validate(
                CandidateList(candidates=[CandidateHypothesis(name=n, website=u, country=c) for n, u, c in _CHINA_AI])
            )
        if schema.__name__ == "SearchQueries" and ("china" in qp or "chinese" in qp) and "ai" in qp:
            return schema.model_validate(
                SearchQueries(
                    queries=[
                        "top Chinese AI companies",
                        "China artificial intelligence suppliers",
                        "Baidu Alibaba Tencent Huawei AI",
                        "Chinese foundation model companies",
                    ]
                )
            )
        if schema.__name__ == "ExtractedFields":
            return schema.model_validate(_fields(_prompt))
        if schema.__name__ in _RESPONSES:
            stored = _RESPONSES[schema.__name__]
            return stored if isinstance(stored, schema) else schema.model_validate(stored)
        return schema.model_construct()

    async def complete(self, prompt: str) -> str:
        return f"[stub-{hashlib.sha256(prompt.encode()).hexdigest()[:8]}] No real LLM configured."
