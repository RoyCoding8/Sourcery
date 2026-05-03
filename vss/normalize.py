from __future__ import annotations

import re

import tldextract
from cleanco import basename
from pypinyin import lazy_pinyin
from unidecode import unidecode


def _is_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def normalize_name(raw: str) -> str:
    cleaned = basename(raw) or raw
    cleaned = " ".join(lazy_pinyin(cleaned)) if _is_cjk(cleaned) else unidecode(cleaned)
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return " ".join(cleaned.lower().split())


def normalize_domain(url: str | None) -> str:
    if not url:
        return ""
    r = tldextract.extract(url)
    return f"{r.domain}.{r.suffix}" if r.domain and r.suffix else ""
