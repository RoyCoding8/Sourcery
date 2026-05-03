from __future__ import annotations

import re

_CERT = re.compile(r"\b(ISO)\s?(\d{3,5})(?::\d{4})?|\b(IATF)\s?16949\b|\b(AS9100|CE|ROHS|REACH|GMP|HACCP|FDA)\b", re.I)
_CATS = {
    "ai": {"ai", "artificial intelligence", "machine learning", "foundation model", "large language model", "llm"},
    "semiconductors": {
        "semiconductor",
        "semiconductors",
        "foundry",
        "wafer",
        "integrated circuit",
        "chip",
        "chips",
        "dram",
        "flash",
    },
}


def certs(text: str) -> set[str]:
    out = set()
    for m in _CERT.finditer(text):
        if m.group(1):
            out.add(f"{m.group(1).upper()} {m.group(2)}")
        elif m.group(3):
            out.add("IATF 16949")
        else:
            out.add(m.group(4).upper())
    return out


def has_category(text: str, category: str) -> bool | None:
    t = text.lower()
    terms = _CATS.get(category.lower())
    if terms is None:
        return None
    return any(re.search(rf"\b{re.escape(term)}\b", t) for term in terms)


def same_category(extracted: str, expected: str) -> bool | None:
    if expected.lower() == extracted.lower():
        return True
    return has_category(extracted, expected)
