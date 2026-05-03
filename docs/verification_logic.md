# Verification Logic

My verification philosophy boils down to a three-step gauntlet. Every supplier candidate has to survive this process before it makes it to the user.

## 1. The Legal Existence Gate
Before we care about what a company makes, we have to prove it legally exists. A candidate *must* be confirmed by at least one of these Tier-A registries:
- **GLEIF**: An exact LEI match, or a fuzzy match (≥0.92) on their normalized legal name.
- **MOEA GCIS**: A business registration match (specific to Taiwan).
- **TWSE MOPS**: A stock listing match (specific to Taiwan).

If a candidate fails all of these, it is immediately dropped. Yes, this means we will occasionally drop a real company that just happens to be missing from these registries. That false-negative cost is acceptable. What is *unacceptable* is a false-positive: handing a buyer a completely fabricated company in their shortlist.

*Example*: TSMC sails through because GLEIF confirms their LEI, MOEA confirms their business accounting number, and TWSE confirms their stock code. But a hallucinated "Taiwan Best Chips Ltd." found in a random DuckDuckGo snippet gets nuked instantly.

## 2. The Operational Reality Check
Once we know they legally exist, we need to prove they actually *do* something. I look for three cheap signals in parallel:
1. **A Live Website**: We hit their primary domain. If it returns a 200 OK, `trafilatura` attempts to scrape product and factory text.
2. **Domain Authority**: We check `crt.sh` (Certificate Transparency logs) to see when their SSL certificates were first issued. If the domain has a history stretching back ≥3 years, it counts as Tier-A evidence. If it was registered last week, it drops to Tier-B. It's incredibly difficult to fake a 5-year cryptographic audit trail.
3. **Web Mentions**: We look for dated mentions in search results via Brave, Tavily, or DDG.

If a company exists legally but fails all operational checks, we still return the candidate, but we hard-cap all their confidence scores to "LOW" and attach a note stating "no operational reality signal found."

## 3. Per-Field Confidence Scoring
We do not assign global confidence scores to suppliers. A company might have a highly verified legal name but a completely unknown employee headcount. Confidence is calculated on a strict, per-field basis using noisy-OR aggregation.

```text
score = 1 - Π(1 − w_i)   [for each distinct piece of corroborating evidence]
```

**The Buckets:**
- **HIGH**: Score ≥ 0.85 *AND* confirmed by ≥ 2 independent sources.
- **MEDIUM**: Score ≥ 0.55.
- **LOW**: Anything below 0.55.

Notice the "two independent sources" rule for HIGH confidence. Even if GLEIF has a 1.00 weight for legal names, the pipeline demands a second source to corroborate it before handing out a HIGH score.

**The Weight Table:**
Different sources have different authorities depending on the field. The full mapping is in `vss/confidence.py`, but generally:
- **GLEIF** is gospel (1.00) for Legal Name and HQ Country, but completely useless for Employee Count.
- **Company Websites** are strong (0.90) for verifying their own URL, but weaker (0.50) for self-reported employee counts.
- **Web Search (Tavily/Brave)** provides weak-to-moderate signals across the board (0.30 - 0.40).

If a source isn't explicitly registered in the weight table, it gets slapped with a deliberately punishing default weight. This forces engineering discipline—you can't sneak a new API into the pipeline and magically get HIGH confidence results without officially declaring how much authority it actually holds.

**Recency Decay:**
Data rots. For volatile fields like `employee_count`, `certifications`, and `product_category`, the weight of the evidence exponentially decays based on how old the snippet is (`exp(−age_days / 365)`). A two-year-old headcount snippet is mathematically worth only 13% of a snippet pulled today. 

**Conflict Resolution:**
If two authoritative sources disagree on a field, the system *never* silently picks a winner. Instead, it surfaces the conflict in `FieldScore.conflicts` for human review, and hard-caps the field's confidence to "MEDIUM", explicitly noting the discrepancy.

## The Judge: Keeping the LLM on a Leash

The `vss/judge.py` module handles the messy unstructured data, but I keep the LLM on a very short leash. 

First, the deterministic stage extracts everything it can using regex and lexicons (certifications, countries, headcounts). The LLM is only invoked for fields that the Python code failed to parse. 

When the LLM *does* return an answer, the output is subjected to rigorous **per-snippet re-verification**:
- If the LLM claims a company makes "Semiconductors", Python code checks if the word "Semiconductor" (or related lexicon terms) actually appears in the snippet the LLM cited.
- If the LLM extracts an employee count, a Python regex runs over the cited snippet to ensure the number actually exists within a ±10% margin.

If the LLM's claim fails this deterministic re-verification, the claim is silently dropped. It doesn't even get downgraded to LOW—it is entirely discarded. Only snippets that mathematically prove the LLM's claim are allowed to contribute to the final confidence score.

### What LLMs are allowed to do:
- Parse natural language queries into structured JSON.
- Generate initial candidate hypotheses (treated as Tier C, unverified data).
- Detect language scripts for normalization routing.

### What LLMs must NEVER do:
- Authoritatively assert cert numbers, headcounts, or revenue.
- Execute entity resolution merges.
- Assign their own confidence scores. Confidence is derived entirely from source authority and corroboration, never from LLM fluency.
