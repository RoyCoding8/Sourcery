# Entity Resolution & Deduplication

## The Challenge

Supplier names are messy. You'll see the exact same company listed as "Foxconn", "Hon Hai Precision Industry Co., Ltd.", and "鴻海精密工業" depending on the source. Naive string matching just doesn't cut it here. The system needs to accurately merge these into a single canonical record without accidentally combining two distinct companies.

## My Approach (Prototype Scale)

For this prototype, we're handling 50 or fewer candidates per query, so I built a deterministic, rules-based pipeline.

### Step 1: Cleaning and Normalization
Before comparing anything, I aggressively clean the data:
- **Stripping Legal Suffixes**: I use `cleanco` to remove over 50 common legal entity types (Inc., GmbH, Co. Ltd., 股份有限公司, etc.).
- **Script Transliteration**: If the name contains CJK characters, I route it through `pypinyin` to convert it to pinyin. For Cyrillic, Arabic, or other scripts, `unidecode` acts as the fallback.
- **Formatting**: Everything gets lowercased, whitespace is collapsed, and lingering punctuation is stripped.

### Step 2: The Merge Logic
Two candidates are merged if they meet **either** of these conditions:
1. **Domain Match**: If both candidates have a website, I normalize the domains (stripping `https://`, `www.`, and trailing paths) and compare them. This is how the system realizes "Foxconn" and "Hon Hai" are the same entity—they both point to `foxconn.com`.
2. **Name Similarity**: I use `rapidfuzz.fuzz.token_set_ratio` with a threshold of 0.85 on the normalized names. Token-set ratio is great because it ignores word order and handles partial overlaps. For example, "Nanya Technology Corporation" and "Nanya Technology Corp" score around 95 and merge perfectly. 

I settled on an 0.85 threshold because pushing it to 0.95 is too strict—it prevents legitimate variants from merging. 0.85 is the sweet spot that catches standard variations while still safely rejecting entirely different companies (e.g., TSMC vs. UMC).

### Step 3: Resolving Conflicts
When two records merge, the system has to pick which data survives:
- **Name**: The longer name wins, as it's usually the more formal/specific one.
- **Website & Country**: The first non-null value is kept.
- **Reason**: The reasoning fields from both candidates are concatenated.

After merging, the normalized name is recalculated from the new combined record to prevent stale data from messing up future comparisons.

### A Note on Cross-Script Safety
I keep the raw script alongside the transliteration, and the system **never merges solely based on transliteration agreement**. For example, 鴻海 (Hon Hai) and 紅海 (Red Sea) both romanize to "Hong Hai." If we blindly merged on pinyin, we'd combine two completely different entities. A cross-script merge strictly requires a matching domain or LEI as a secondary signal.

## How I'd Scale This for Production

If this were handling 10,000+ records, the O(n²) pairwise comparison would choke. Here’s how I'd evolve it:

1. **Canopy Clustering (Blocking)**: Instead of comparing everything to everything, I'd group candidates by the first 3 characters of their normalized name plus their country. We'd only run fuzzy matching within these "canopies," drastically reducing the computational load.
2. **GLEIF Parent-Child Rollups**: The GLEIF database actually tracks corporate hierarchies. I'd use this to automatically link subsidiaries to their parents (e.g., linking TSMC Nanjing to TSMC). I skipped this for the prototype because it requires extra API calls per entity, which burns through rate limits fast.
3. **Persistent Canonical-ID Ledger**: In production, every resolved entity needs a stable UUID stored in a database like Postgres. New data ingestions would anchor to these existing records via LEI or domain matches, preventing duplicates from accumulating over time.
4. **Active Learning**: I'd replace the hardcoded 0.85 threshold with an ML classifier (like `dedupe` or `splink`). We could build an internal tool that surfaces borderline matches (say, 0.80 to 0.90 similarity) to human reviewers. Their decisions would feed back into the model to continuously improve accuracy.

## Known Failure Modes

This setup isn't perfect. Here's where it currently breaks down:
- **Transliteration Collisions**: If we get two companies that romanize to the same name (like the Hong Hai example above) and neither has a website or LEI on file, the system can't distinguish them.
- **Radically Different Subsidiary Names**: If a parent company owns a subsidiary with a completely different name and domain (e.g., Foxconn owning Sharp), string matching won't catch it. We'd absolutely need GLEIF's relationship data for this.
- **Historical Rebrands**: If a company changes its name but hasn't updated its business registries, it might appear as two separate entities in the system.
- **Language Bias**: The 0.85 fuzzy match threshold is heavily tuned for English and CJK names. It might need tweaking for Arabic or Cyrillic naming conventions.
