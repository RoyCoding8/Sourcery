from __future__ import annotations

import asyncio
import csv
import json
import sys
from pathlib import Path

import typer

from vss.pipeline import run

FLAT_FIELDS = [
    "canonical_supplier_name",
    "website",
    "country_region",
    "product_category",
    "certifications",
    "employee_count",
]


def _flatten(rec: dict) -> dict:
    flat = {}
    for field in FLAT_FIELDS:
        score = rec.get(field, {})
        flat |= {
            field: score.get("value", ""),
            f"{field}_confidence": score.get("confidence", ""),
            f"{field}_reason": score.get("reason", ""),
            f"{field}_sources": "; ".join(e.get("source", "") for e in score.get("evidence", [])),
        }
    return flat | {"notes": rec.get("notes", "")}


def main(
    query: str = typer.Argument(..., help="Natural language supplier query"),
    out: str = typer.Option("outputs/run", help="Output directory"),
    provider: str = typer.Option("", help="LLM provider"),
    model: str = typer.Option("", help="LLM model"),
) -> None:
    try:
        result = asyncio.run(run(query, provider or None, model or None))
    except Exception as e:
        typer.echo(f"ERROR: {e}", err=True)
        sys.exit(1)

    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)
    data = result.model_dump()
    (outdir / "suppliers.json").write_text(json.dumps(data, indent=2, default=str))

    rows = [_flatten(s) for s in data["suppliers"]]
    if rows:
        with (outdir / "suppliers.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)

    typer.echo(f"OK {len(result.suppliers)} suppliers -> {outdir}")
    if result.partial:
        typer.echo("WARNING: Partial results - some sources timed out.", err=True)


def app() -> None:
    typer.run(main)


if __name__ == "__main__":
    app()
