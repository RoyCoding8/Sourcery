from __future__ import annotations

import asyncio

from vss.models import Evidence
from vss.sources import brave, gleif, iaf_certsearch, moea_taiwan, ops_reality, sanctions, twse, web, website


async def _entity(fn, name, country, _q, _url):
    return await fn(name, country)


async def _query(fn, _name, _country, q, _url):
    return await fn(q)


async def _site(fn, name, country, _q, url):
    return await fn(name, country, url=url) if url else []


REGISTRY = {
    "gleif": lambda *a: _entity(gleif.lookup, *a),
    "moea": lambda *a: _entity(moea_taiwan.lookup, *a),
    "twse": lambda *a: _entity(twse.lookup, *a),
    "iaf": lambda *a: _entity(iaf_certsearch.lookup, *a),
    "sanctions": lambda *a: _entity(sanctions.lookup, *a),
    "brave": lambda *a: _query(brave.search, *a),
    "web": lambda *a: _query(web.search, *a),
    "website": lambda *a: _site(website.lookup, *a),
    "ops": lambda *a: _site(ops_reality.lookup, *a),
}


def _expand(template: str, name: str) -> str:
    return template.replace("{name}", name).strip()


async def gather(
    name: str,
    country: str | None,
    url: str | None,
    queries: list[str],
    sources: list[str],
) -> list[Evidence]:
    expanded = [_expand(q, name) for q in queries] or [name]
    tasks = []
    for s in sources:
        fn = REGISTRY.get(s)
        if not fn:
            continue
        if s in ("brave", "web"):
            tasks.extend(fn(name, country, q, url) for q in expanded)
        else:
            tasks.append(fn(name, country, expanded[0], url))
    if not tasks:
        return []
    res = await asyncio.gather(*tasks, return_exceptions=True)
    out: list[Evidence] = []
    for r in res:
        if isinstance(r, list):
            out.extend(r)
    return out


__all__ = ["REGISTRY", "gather", "sanctions", "web", "website"]
