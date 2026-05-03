# Tools & Stack

Here's a breakdown of the specific tools I chose to build this pipeline, why I picked them over the obvious alternatives, and where their limitations lie.

## NLP & Query Parsing
**The Stack:** Direct LLM API calls via native `tool_use` / structured output. I built a lightweight adapter protocol supporting Bedrock, Anthropic, OpenAI, Gemini, Groq, Ollama, and a mock Stub.

**The "Why":** Using Pydantic schemas mapped to JSON schemas combined with native LLM tool-calling is the absolute best way to get type-safe, structured data out of natural language. I specifically rejected heavier frameworks like `langchain` or `instructor`. They add 50MB+ of unnecessary abstraction over what is essentially a 20-line API wrapper. I want to see and control the raw tool-calling payloads directly. I also rejected regex parsing because it simply can't handle complex, multi-clause queries like "ISO-certified PCB manufacturers in Southeast Asia with 500+ employee capacity."

**Where it breaks:** Vague queries ("find good suppliers") result in empty SearchCriteria fields. The LLM is strictly a parser here—it doesn't invent criteria, so downstream filters have nothing to work with.

## Web Search & Data APIs
**The Stack:** Tavily (Primary), Brave Search (Secondary), DuckDuckGo via `ddgs` (Zero-cost fallback).

**The "Why":** I chose Tavily over SerpAPI because it returns highly structured results with excellent content snippets in a single call, and its 1K/month free tier is perfect for prototyping (SerpAPI costs $50/mo). I added Brave to ensure we have a secondary signal from a completely independent, non-Google-derived search index. Finally, `ddgs` acts as the safety net—it requires no API keys and runs nicely in an `asyncio.to_thread` wrapper so it doesn't block the event loop.

**Where it breaks:** All three suffer from recency bias, often surfacing marketing press releases instead of hard operational data. Furthermore, DDG will aggressively block automated requests if pushed too hard.

## Entity Matching
**The Stack:** `rapidfuzz` + `cleanco` + `pypinyin` + `unidecode`.

**The "Why":** I rejected ML-based deduplication libraries like `dedupe` or `splink` because they require labeled training data and an explicit training step. For a prototype dealing with ≤50 candidates per run, deterministic fuzzy matching with conservative thresholds is significantly faster, simpler, and fully auditable. 

To clean the data, I use `cleanco` to strip over 50 variations of legal suffixes (GmbH, S.A., Co. Ltd., 股份有限公司). To handle cross-script matching, I use `pypinyin` to convert Chinese characters into tone-marked pinyin, and `unidecode` for everything else (Arabic, Cyrillic, etc.). Relying on an LLM to handle transliteration would introduce unacceptable non-determinism into the core resolution logic. `rapidfuzz` was chosen because its C++ backend is roughly 100x faster than traditional `fuzzywuzzy`.

**Where it breaks:** This stack can't resolve subsidiaries with completely unrelated names (e.g., Foxconn owning Sharp) without external relationship data. It also requires careful threshold tuning for non-Latin scripts.

## Website Content Extraction
**The Stack:** `trafilatura`

**The "Why":** I chose this over `beautifulsoup4` because BeautifulSoup expects you to write custom CSS selectors for every site. `trafilatura` uses statistical models to automatically identify and extract the "main content" of a page while stripping out the navigation, footers, cookie banners, and ads. I also rejected `newspaper3k` because it's heavily optimized for news articles (seeking headlines and bylines), whereas we need to scrape product catalogs and corporate 'About Us' pages.

**Where it breaks:** Single Page Applications (SPAs) that heavily rely on client-side JavaScript rendering will return empty content, as `trafilatura` doesn't execute JS. A production environment would need a Playwright fallback.

## Storage & Normalization
**The Stack:** Pydantic models dumped to the standard library `json` and `csv` modules. No database.

**The "Why":** I explicitly rejected `pandas`. Pulling in a massive data science dependency just to write a 25-column flat table to a CSV is overkill and bloats the deployment bundle. The standard library handles this perfectly in five lines of code. I skipped SQLite/Postgres because this prototype is stateless. 

**Where it breaks:** Without a database, there is no persistent canonical-ID ledger. Every query runs in isolation, meaning we can't anchor new data to historically verified entities.

## The Output Layer
**The Stack:** Next.js 15 (App Router) + Tailwind CSS for the optional web UI. Python dev server for the local API.

**The "Why":** I chose Next.js over Streamlit because it gives me total control over the UI and a real URL structure. Streamlit's widget model is great for notebooks but feels clunky for a polished prototype. The UI is intentionally lean (just a QueryForm, SupplierCard, and EvidenceList). For the backend, Next.js proxy rewrites seamlessly route `/api/*` traffic to the local Python dev server during development.

**Where it breaks:** Without Server-Sent Events (SSE) or WebSockets, the UI blocks until the entire pipeline finishes (~5-15 seconds depending on external API latency). A production build would absolutely need progressive result streaming.
