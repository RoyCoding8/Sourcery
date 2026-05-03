# Source Strategy & Ordering

## My Stance: Registries First, LLMs Last

My approach to sourcing is simple: anchor on authoritative registries first, and use LLMs strictly as a fallback or a hypothesis generator—never as a primary source of fact. 

It's tempting to build an LLM-first pipeline because it's much faster to prototype. But doing so inverts the trust model: you start with a pile of unverified, hallucination-prone claims and try to prove them true, which creates a huge confirmation bias. By putting registries first, every candidate that enters the pipeline starts with at least one piece of hard, Tier-A evidence attached to it.

During the candidate generation phase, the LLM does run in parallel with web searches, but any output it generates is explicitly tagged as "Tier C." A data point confirmed *only* by an LLM will never climb above a "LOW" confidence score, no matter how confident or fluent the LLM sounds.

## Generation Strategy

Here's how I generate the initial candidate list, running these paths concurrently:

1. **GLEIF (Authoritative Bootstrap):** I seed the query using the GLEIF API, pulling real, LEI-registered entities based on the requested country and product keywords. This is the gold standard.
2. **Tavily Search (Web Discovery):** Provides structured web results with decent content snippets.
3. **Brave Search (Secondary Web Discovery):** A great complement to Tavily that uses an independent search index.
4. **DuckDuckGo (Zero-Cost Fallback):** If Tavily and Brave exhaust their free API limits, `ddgs` kicks in as a fallback.
5. **LLM Hypothesis (Long-Tail Backstop):** I ask the LLM to brainstorm candidates. This catches well-known companies that might have slipped past the specific search queries, but they remain Tier C until proven otherwise.

All results are merged and deduplicated. If the GLEIF seed and the LLM hypothesis find the exact same company, the GLEIF record (with its LEI) survives the deduplication and anchors the entity.

## The Two-Pass Verification Budget

To keep API spend reasonable and execution time low, verification runs in two passes:

**Pass 1 (Cheap & Fixed Cost):** 
Every candidate runs through this pass. It hits GLEIF, MOEA, TWSE, and IAF (which are all cheap, single-HTTP calls by name), fetches the company's website via `trafilatura`, and runs a Domain Authority check against `crt.sh`. 

**Pass 2 (Expensive & Conditional):**
This pass involves firing up Brave, Tavily, and DuckDuckGo to run targeted web searches. Because these are expensive, Pass 2 *only* fires for specific fields that failed to reach a "MEDIUM" confidence score (0.55) during Pass 1. For a major company like TSMC, Pass 1 easily pushes their name, country, and website to HIGH confidence. Pass 2 only triggers to hunt down harder fields like `employee_count` or obscure `certifications`. This strategy essentially halves the API spend for well-covered candidates.

## The Verification Waterfall

When verifying data, here's how I rank the authority of the sources:

* **Tier A (Registries):** GLEIF, MOEA (Taiwan business registry), TWSE (Taiwan stock exchange), IAF CertSearch, and OFAC SDN. These are authoritative, but they have coverage gaps (e.g., GLEIF misses 90% of Vietnamese SMEs).
* **Tier A (Technical Signals):** Domain Authority via Certificate Transparency (`crt.sh`). If a company claims to have been around for 20 years but their domain was registered last Tuesday with no certificate history, the CT log makes that lie easy to detect.
* **Tier B (Web & Operations):** Brave, Tavily, and the company's own website. These provide operational reality but suffer from recency bias (e.g., surfacing a recent press release instead of hard facts).
* **Tier C (LLMs):** Purely for hypothesis generation.

Authority is calculated on a per-field basis. GLEIF is treated as absolute truth (weight `1.00`) for a company's legal name, but it is effectively ignored when trying to determine employee headcount.

## Dealing with Thin Coverage

What happens when we hit a region with terrible registry coverage? The system relies on Pass 2 (web search + company website) to verify the data. Because it lacks Tier-A registry confirmation, the confidence scores will max out at "MEDIUM." 

The pipeline will *never* silently promote a Tier-B result to "HIGH" confidence. To get a HIGH score, the system requires an aggregated score of ≥ 0.85 *and* at least two independent sources. Two Tier-B web sources simply don't carry enough mathematical weight to clear that bar without a Tier-A source backing them up. 

I designed it this way because false negatives (dropping a real supplier) are acceptable, but false positives (telling a buyer an unverified supplier is highly trusted) are catastrophic.
