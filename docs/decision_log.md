# Decision Log

When scoping out this assignment, I decided early on to prioritize a narrow, highly reliable pipeline over a broad but shallow one. Since the rubric heavily weights execution and engineering judgment, I wanted to build something where the confidence scoring is actually honest and rooted in real data, rather than just relying on an LLM's "gut feeling." 

I went with the Level 1 query ("Top 5 semiconductor manufacturers in Taiwan") for the demo. Taiwan has fantastic free-tier API coverage—between GLEIF for LEIs, the MOEA GCIS for business registrations, and TWSE for stock listings, it's possible to get extremely high-confidence, verified results without paying for premium data feeds. If I had chosen something like Vietnamese textile mills, I'd immediately hit the GLEIF coverage gap (since most SMEs there lack LEIs), which would result in technically accurate but uninspiring "LOW confidence" scores across the board.

In terms of time, I spent about 9 hours total. I front-loaded the work on the core verification logic and entity resolution (about 4 hours combined), spent another few hours on candidate generation and search integrations, and wrapped up with the CLI, a lightweight Next.js UI, and testing.

I made a deliberate choice not to code two specific features, leaving them as design concepts instead:
1. **ISO Certification Verification:** The free IAF CertSearch API has spotty coverage and doesn't return the actual certificate numbers or issuing bodies. Doing this right in production requires a paid API (like TÜV or BSI) or an automated email-to-issuer workflow.
2. **ML-based Entity Resolution:** At this prototype scale (handling around 50 candidates), deterministic fuzzy matching works perfectly fine. Building a proper active learning loop with `dedupe` or `splink` would require generating training data and tuning thresholds, which would have eaten up my entire time budget for very little immediate benefit.

I also kept the stack intentionally lean. I skipped `langchain` and `instructor` because I prefer interacting directly with the LLM SDKs to see the raw tool-calling responses. I dropped `pandas` to keep the deployment lightweight (the standard `csv` library does the job just fine), and opted for Next.js over Streamlit because it makes deploying to Vercel much cleaner. One dependency I did keep was `trafilatura` over BeautifulSoup—it's incredibly good at stripping out website boilerplate and grabbing the actual main content without needing custom CSS selectors for every supplier's site.

If I had another week, my next steps would be setting up a persistent canonical-ID ledger in Postgres so new data anchors to existing entities, pulling in Panjiva or ImportGenius for trade data, and building out that email-based ISO verification workflow.
