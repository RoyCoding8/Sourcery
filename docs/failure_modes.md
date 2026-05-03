# Failure Modes

No system is perfect, especially when dealing with messy global supply chain data. Here are the specific areas where this prototype currently falls short, along with how I'd address them in a production environment.

## 1. The SME Coverage Gap (Vietnam/Indonesia)
Roughly 90% of small and medium enterprises (SMEs) in countries like Vietnam and Indonesia don't have LEIs registered in the GLEIF database. If a user queries "textile mills in Vietnam with <200 employees," the system will find candidates via web search, but the confidence scores for their names and locations will cap out at "MEDIUM." We lack that Tier-A registry confirmation. While it's honest reporting, a customer might be frustrated that they can't get HIGH confidence results in these regions.
**How to fix it:** We'd need to scrape or integrate with local, country-specific registries (like the DKKD in Vietnam or AHU Online in Indonesia). I skipped this for the prototype because they often involve CAPTCHAs and brittle web scraping.

## 2. ISO Certification Verification
Right now, verifying specific ISO certifications is an unsolved problem using only free APIs. The IAF CertSearch database has limited coverage, and its API doesn't return the actual certificate numbers or the issuing bodies. If a user asks for "ISO 9001 certified PCB manufacturers," the system can flag that they claim to be certified (scoring it as MEDIUM confidence), but it can't mathematically prove the cert is valid.
**How to fix it:** Production requires either integrating with paid compliance APIs (like Ecovadis or Sedex) or building an automated workflow that emails the issuing body (BSI, TÜV, etc.) to confirm the cert number.

## 3. Pinyin Transliteration Collisions
Any query involving Chinese company names runs the risk of transliteration collisions. For instance, 鴻海 (Hon Hai / Foxconn) and 紅海 (Red Sea) both romanize to "Hong Hai." 
**Mitigation in place:** I built a safeguard where the system refuses to merge records across different scripts unless there's a matching domain name or LEI. 
**Remaining risk:** If two colliding companies *both* lack a website and an LEI, the system might falsely merge them. 

## 4. API Rate Limits & Exhaustion
The prototype relies on free tiers for web searches: Tavily gives 1K requests/month, and Brave gives 2K/month. If we burn through these, the system degrades to using DuckDuckGo via the `ddgs` library combined with LLM hypotheses. Since DDG doesn't use an API key, it's prone to rate-limiting or blocking automated requests. If this happens, the user will see fewer candidates and lower confidence scores without an obvious explanation.
**How to fix it:** In production, this is solved by paying for enterprise API tiers and implementing aggressive caching (like Redis) so we don't re-fetch the same searches during iteration.

## 5. Brittle Government APIs
The Taiwan MOEA GCIS API (`data.gcis.nat.gov.tw`) is a classic government endpoint: no SLAs, no versioning, and no changelogs. If they tweak their OData filter syntax tomorrow, our queries will break. It also throws random 500 errors occasionally.
**Mitigation in place:** I designed the pipeline to be resilient to this. If the API errors out, the source just returns an empty list rather than crashing the whole pipeline.

## 6. Private Company Headcounts
The `employee_count` field is notoriously difficult to verify for private companies. The system extracts headcount numbers from company websites using regex, which works great for massive corps like TSMC that boast about having "73,000+ employees" on their homepage. But many suppliers simply don't publish this. If a user filters by "500+ employees", companies that don't publish their headcount are excluded.
**Mitigation in place:** Rather than letting the LLM hallucinate a number, the field safely returns null with a LOW confidence score, citing "no public headcount source."

## 7. LLM Hallucinations on "Stub" Runs
If the pipeline is run using the `stub` LLM provider (meaning no real API keys are configured), it relies entirely on hardcoded fixture data. It works perfectly for the Level 1 demo query, but will return absolute garbage for anything else. Even with a real LLM, if the search APIs are exhausted, the candidates are generated purely from the LLM's internal weights.
**Mitigation in place:** The system is aggressively transparent about this. Every field shows its exact evidence chain. If a buyer sees "LLM hypothesis only," they know exactly how much to trust it.

## 8. Stale Sanctions Data
The OFAC sanctions check relies on a static, local CSV file (`data/ofac_sdn.csv`). If this file isn't updated regularly, newly sanctioned entities will slip right through. 
**How to fix it:** The system needs a scheduled cron job to automatically pull the latest SDN list daily. 

## 9. Pipeline Timeout on Slow APIs
The pipeline is highly concurrent, fanning out to query 7 sources for 5 candidates (35 HTTP requests total). While `asyncio.gather` helps, if external APIs like GLEIF are having a slow day, the total execution time can easily blow past reasonable timeouts (especially in serverless or constrained environments).
**Mitigation in place:** If a timeout is looming, the pipeline catches it and returns `partial: true` to the UI, so the user at least gets the data that *did* complete rather than a generic timeout error.

## 10. The Ultimate Customer Complaint
If you put this in front of a real procurement team tomorrow, their first complaint would be: *"Why can't I search for suppliers in [Obscure Region] and get HIGH confidence results?"* 
The hard truth is that free-tier APIs and global registries like GLEIF have massive coverage gaps outside of major western economies and specific tech hubs like Taiwan. Without building bespoke integrations for every local domestic registry on earth, the best we can offer for those regions is MEDIUM confidence based on web search corroboration. That is the fundamental ceiling of a free-API approach.
