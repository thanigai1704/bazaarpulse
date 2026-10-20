# BazaarPulse — Market Analysis Writeup

**Dataset:** Flipkart product catalogue snapshot (20,000 raw rows → 12,620 cleaned listings)
**Source:** PromptCloudHQ/flipkart-products (public HuggingFace mirror), crawled 2018
**Stack:** Python (pandas/numpy) → FastAPI `/analysis` endpoint → Next.js charts
**Reproduce:** `python scripts/fetch_real_dataset.py && python scripts/load_kaggle_dataset.py --csv data/flipkart_products.csv --data-source flipkart_2018 --replace`

---

## 1. Data cleaning & provenance

Raw dump → analysis-ready table. Every transformation is in
`backend/scripts/load_kaggle_dataset.py`:

| Step | Detail |
| --- | --- |
| Deduplicate | 20,000 → 17,692 unique product names → **12,620** after dropping rows with unusable prices |
| Price parsing | `"₹1,45,999"` / `"1,45,999"` → integer; `discounted_price` treated as MRP fallback |
| Discount | `discount_pct = (mrp − price) / mrp × 100`; enforced `mrp = max(mrp, price)` |
| Category tree | `'["Clothing >> Women\'s Clothing >> …"]'` → root bucket (`Clothing`); sparse buckets (<50 listings) pooled into `Other` → **21 categories** |
| Images | JSON-encoded URL list → highest-res (1100×1100) variant; **99.8% coverage** |
| Primary key | Deterministic `fk-{sha1(uniq_id)}` — hex digests preserved (an earlier digit-stripping version collided on UNIQUE) |
| Provenance | `data_source='flipkart_2018'` on every row; re-imports are idempotent via `--replace` |

## 2. Dataset at a glance

| Metric | Value |
| --- | --- |
| Listings | 12,620 |
| Categories (root) | 21 |
| Distinct brands | 3,454 |
| Price range | ₹35 – ₹5,71,230 |
| Median price | **₹599** |
| Mean price | **₹2,163** (3.6× the median) |
| Mean / median discount | 38.6% / 42.2% |
| Listings carrying a discount | **87.1%** |
| Star-rating coverage | **10.4%** (1,313 of 12,620) |

## 3. Findings

### 3.1 Prices are right-skewed — never report the mean alone

Every large category has CV > 1 and skew > 15, meaning a handful of luxury
listings drag the mean far above the typical price:

| Category | Median | Mean | CV | Skew |
| --- | --- | --- | --- | --- |
| Watches | ₹767 | ₹2,568 | **10.41** | 19.2 |
| Mobiles & Accessories | ₹400 | ₹912 | 5.97 | 20.4 |
| Clothing | ₹550 | ₹785 | 1.54 | 24.7 |
| Kitchen & Dining | ₹299 | ₹541 | 2.17 | 16.5 |

**So-what:** catalogue-wide, the mean price (₹2,163) is **3.6× the median (₹599)**.
Any dashboard or slide that leads with "average price" overstates the typical
listing by hundreds of rupees. Medians and IQRs are used throughout this project.

### 3.2 Discounts are near-universal and deepest where list prices are inflated

87.1% of listings carry a markdown. Mean discount by category:

| Category | Mean disc. | Median disc. | Share discounted |
| --- | --- | --- | --- |
| Automotive | **55.0%** | 62.4% | 98.6% |
| Mobiles & Accessories | 51.6% | 53.4% | 96.6% |
| Bags, Wallets & Belts | 46.1% | 53.5% | 90.2% |
| Kitchen & Dining | 44.0% | 52.5% | 92.6% |
| Computers | 43.3% | 46.3% | 94.9% |

Where median > mean (Bags, Kitchen), the average is *pulled down* by a long
left tail of lightly-discounted items — the mirror image of the price skew.

**So-what:** a "50% off" badge in Automotive/Mobiles is table stakes, not a
differentiator. The MRP-strike-through is an anchoring device, not evidence of
a deal.

### 3.3 Deep discounts do not buy better reviews

Pearson correlation on the 1,313 rated listings:

| Pair | r | n |
| --- | --- | --- |
| Discount % vs star rating | **+0.014** | 1,313 |
| log(price) vs star rating | +0.050 | 1,313 |
| Price vs discount % | −0.140 | 12,620 |

**So-what:** the discount-rating relationship is effectively zero. Price
anchoring (deep strike-throughs on low-ticket items) inflates perceived value
without translating into satisfaction — useful evidence against "discount hard
to win the ratings game."

### 3.4 The brand landscape is fragmented — but with a long tail

Herfindahl-Hirschman Index on listing share = **0.0908** (below the 0.15
"competitive" threshold). Top-5 brands hold 37.0% of listings; top-10 hold 40.8%.
The Pareto count: **1,045 brands (30% of all brands) produce 80% of the
catalogue** — and ~30% of rows carry no brand at all ("Unknown").

**So-what:** no brand-level moat exists in this marketplace snapshot. Shelf space
is won category-by-category, not by a handful of giants.

### 3.5 8% of the catalogue are extreme price outliers

Rule: price > 5× own category median → **1,015 listings (8.0%)**, median price
₹15,552. Top flags:

| Product | Price | Category median | × median |
| --- | --- | --- | --- |
| Breitling Chronomat 44 | ₹5,71,230 | ₹767 | **744.8×** |
| Audeze LCD2 planar headphones | ₹1,16,292 | ₹400 | 290.7× |
| Cartier W6701005 | ₹2,01,000 | ₹767 | 262.1× |
| TAG Heuer Formula 1 | ₹1,07,750 | ₹767 | 140.5× |

**So-what:** luxury watches/jewellery sit in the same category buckets as ₹500
fashion items. Category medians (not means) must anchor any price-fairness or
deal-scoring feature, or luxury SKUs will permanently poison the baselines.

### 3.6 Selection bias: ratings are missing not-at-random

Only 10.4% of listings have a star rating, and rated listings are **cheaper and
less discounted** than unrated ones:

| | Rated | Unrated |
| --- | --- | --- |
| Mean price | **₹1,257** | **₹2,269** |
| Mean discount | 35.2% | 39.0% |

**So-what:** rating-derived metrics describe a biased subsample (lower-ticket,
less-promoted goods). Any "what do customers love" analysis on this dump must
state this limitation — and it is surfaced in the UI's data-quality panel.

## 4. What the app shows

The **Analysis** tab (`/analysis`, served by `GET /api/analysis`, computed
on-demand by `backend/app/services/analysis.py`) renders:

- Price dispersion per category (median vs mean bars + full quartile table)
- Discount depth per category (mean vs median + share discounted)
- Brand concentration (HHI, top-brand Pareto chart)
- Pearson correlations with sample sizes and caveats
- Price-outlier table with ×-median multipliers
- Data-quality panel exposing the rating-coverage and selection-bias numbers

## 5. Limitations

- The snapshot is from **2018** — prices reflect that crawl date, not today's market.
- Rating coverage (10.4%) makes rating-based conclusions directional, not conclusive.
- Correlations are descriptive (no significance testing); r-values near zero are
  reported as "no evidence of relationship," not "proof of none."
- Root-category collapsing pools genuinely different sub-markets (e.g. all
  Clothing); sub-category analysis is one flag away (`--category-depth 2`).
