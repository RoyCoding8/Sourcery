"""Quick smoke test — runs the stub pipeline and prints summary."""
import asyncio

from vss.pipeline import run


async def main() -> None:
    result = await run("Top 5 semiconductor manufacturers in Taiwan", provider="stub")
    print(f"OK: {len(result.suppliers)} suppliers")
    for s in result.suppliers:
        print(f"  {s.canonical_supplier_name.value} [{s.canonical_supplier_name.confidence}]")


if __name__ == "__main__":
    asyncio.run(main())
