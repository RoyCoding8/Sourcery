# SOURCERY

> `source` + `sorcery` — supplier search that actually checks its sources.

You give it a natural language query like *"Top 5 semiconductor manufacturers in Taiwan"* and it goes out, finds candidates, cross-references them against real registries (GLEIF, MOEA, TWSE, OFAC, IAF), and comes back with per-field confidence scores. If it can't verify something, it says so honestly instead of making things up.

## Get started

You'll need Python 3.12+, [uv](https://docs.astral.sh/uv/), and Node.js 18+.

```bash
cp .env.example .env          # add your API keys, or leave blank for stub mode
uv sync --all-extras          # python deps
npm ci                        # frontend deps (skip if you only want the CLI)
```

### CLI

Works out of the box with `--provider stub` (no API keys, uses hardcoded test data):

```bash
uv run sourcery "Top 5 semiconductor manufacturers in Taiwan" --out outputs/my_run --provider stub
```

With a real LLM (set your keys in `.env` first):

```bash
uv run sourcery "Top 5 semiconductor manufacturers in Taiwan" --out outputs/my_run
```

### Web UI

Two terminals:

```bash
# API server
uv run python scripts/dev_server.py

# Frontend
npm run dev
# → http://localhost:3000
```

### Tests

```bash
uv run pytest -q
```

## How it works

```
                          ┌─────────────────────────────────────────────┐
  "Top 5 semiconductor    │                  PIPELINE                   │
   manufacturers in       │                                             │
   Taiwan"                │  ┌─────────┐   ┌────────────┐   ┌───────┐  │
        ──────────────────┤► │ Parser  │──►│ Candidates │──►│Resolve│  │
                          │  │ (LLM)   │   │ Tavily+DDG │   │(fuzzy)│  │
                          │  └─────────┘   │ +LLM hypo  │   └───┬───┘  │
                          │                └────────────┘       │      │
                          │                                     ▼      │
                          │  ┌──────────────────────────────────────┐  │
                          │  │        Evidence Gathering            │  │
                          │  │  GLEIF · MOEA · TWSE · OFAC · IAF   │  │
                          │  │  Brave Search · Company Website      │  │
                          │  └──────────────────┬───────────────────┘  │
                          │                     ▼                      │
                          │  ┌──────────────────────────────────────┐  │
                          │  │     Per-Field Confidence Scoring     │  │
                          │  │  HIGH: ≥2 Tier-A or 1A+1B           │  │
                          │  │  MEDIUM: 1 Tier-A or ≥2 Tier-B      │  │
                          │  │  LOW: single source or LLM-only     │  │
                          │  └──────────────────┬───────────────────┘  │
                          │                     ▼                      │
                          │              JSON + CSV export             │
                          └─────────────────────────────────────────────┘
```

The key idea: registries first, LLM last. If GLEIF says a company exists, that's a HIGH confidence signal. If only the LLM thinks so, that's LOW. The tool is honest about what it knows and what it's guessing.

## LLM Providers

Set `LLM_PROVIDER` in `.env`, or pick one from the `/providers` page in the web UI.

| Provider | Key | Notes |
|----------|-----|-------|
| `bedrock` | AWS credentials | Converse API with tool_use |
| `anthropic` | `ANTHROPIC_API_KEY` | Direct API |
| `openai` | `OPENAI_API_KEY` | Direct API |
| `gemini` | `GEMINI_API_KEY` | Google GenAI |
| `groq` | `GROQ_API_KEY` | Fast inference |
| `ollama` | `OLLAMA_BASE_URL` | Local models |
| `stub` | None | Hardcoded fixtures, no network calls |

## Docs

The hard problems and how we solved them:

- [Source Strategy](docs/source_strategy.md) — why registries come first
- [Verification Logic](docs/verification_logic.md) — how confidence scoring works
- [Entity Resolution](docs/entity_resolution.md) — matching companies across scripts and aliases
- [Failure Modes](docs/failure_modes.md) — what breaks and how we handle it
- [Tools & Stack](docs/tools_stack.md) — why each dependency is here
- [Decision Log](docs/decision_log.md) — tradeoffs we made along the way

## Project layout

```
vss/                       # the engine
├── pipeline.py            # orchestrates everything
├── parser.py              # turns your query into structured criteria
├── candidates.py          # finds supplier candidates (Tavily + DDG + LLM)
├── resolve.py             # deduplicates via fuzzy matching
├── normalize.py           # handles CJK, transliteration, legal suffixes
├── confidence.py          # scores each field based on evidence quality
├── models.py              # Pydantic schemas
├── cli.py                 # CLI entry point
├── sources/               # registry adapters (GLEIF, MOEA, TWSE, etc.)
└── llm/                   # 7 provider adapters behind a common Protocol
app/                       # Next.js frontend
components/                # React UI
api/                       # serverless API layer
tests/                     # pytest suite
```

## License

Apache 2.0
