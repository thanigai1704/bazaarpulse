#!/usr/bin/env python
"""Generate the BazaarPulse seed dataset (realistic Indian e-commerce data).

WHY THIS EXISTS
───────────────
Flipkart & Amazon.in block large-scale scraping, and Kaggle datasets are a
nice-to-have but give you zero control over shape. This generator produces a
*realistic, self-contained* snapshot of the Indian market so the portfolio
demo runs offline with zero external dependencies:

    * 36 hand-curated products across Smartphones / Laptops / Home Appliances,
      priced in ₹ (Indian grouping: 1,45,999) and named the way Flipkart and
      Amazon.in list them (e.g. "Samsung Galaxy S24 Ultra 5G (Titanium Gray,
      256 GB)").
    * ~5-8 reviews per product, written in Hinglish-flavoured Indian-English
      with realistic star ratings.
    * Every review pre-tagged with a sentiment label/score (computed with the
      same lexicon fallback the API uses, so seed data needs no LLM).

USAGE
─────
    python scripts/generate_seed_data.py          # writes data/seed_products.json
    python scripts/seed_db.py                     # loads JSON into the database

You can replace the generated file with any Kaggle "Flipkart/Amazon India"
CSV — see scripts/load_kaggle_dataset.py for that path.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Deterministic-ish randomness so re-running is stable enough to diff.
random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "seed_products.json"

# ─────────────────────────────────────────────────────────────────────────
# Product catalogue: (name, brand, category, mrp, price, rating, rating_count)
# Prices are in ₹. MRP vs price produce believable discount percentages.
# ─────────────────────────────────────────────────────────────────────────
CATALOGUE = [
    # ── Smartphones ─────────────────────────────────────────────────────
    ("Samsung Galaxy S24 Ultra 5G (Titanium Gray, 256 GB)", "Samsung", "Smartphones", 129999, 109999, 4.6, 3421),
    ("Samsung Galaxy S24 FE 5G (Graphite, 128 GB)", "Samsung", "Smartphones", 59999, 47999, 4.3, 1210),
    ("Samsung Galaxy M35 5G (Thunder Gray, 128 GB)", "Samsung", "Smartphones", 24999, 19999, 4.4, 2890),
    ("Samsung Galaxy A35 5G (Awesome Navy, 128 GB)", "Samsung", "Smartphones", 29999, 25999, 4.2, 731),
    ("Redmi Note 14 Pro 5G (Phantom Purple, 8GB/256GB)", "Xiaomi", "Smartphones", 29999, 24999, 4.5, 5230),
    ("Redmi 13C 5G (Starlight Black, 4GB/128GB)", "Xiaomi", "Smartphones", 12499, 9999, 4.1, 8910),
    ("Xiaomi 14 5G (Black, 12GB/512GB)", "Xiaomi", "Smartphones", 69999, 59999, 4.4, 512),
    ("OnePlus 12 5G (Flowy Emerald, 16GB/256GB)", "OnePlus", "Smartphones", 64999, 56999, 4.5, 2210),
    ("OnePlus 12R 5G (Cool Blue, 8GB/128GB)", "OnePlus", "Smartphones", 39999, 33999, 4.3, 1745),
    ("OnePlus Nord CE 4 5G (Dark Chrome, 8GB/128GB)", "OnePlus", "Smartphones", 24999, 20999, 4.2, 2087),
    ("realme GT 6 5G (Razor Green, 8GB/256GB)", "Realme", "Smartphones", 42999, 35999, 4.4, 986),
    ("realme Narzo 70 Pro 5G (Glass Green, 8GB/128GB)", "Realme", "Smartphones", 23999, 18999, 4.3, 3645),
    ("realme P1 5G (Sunny Oasis, 8GB/128GB)", "Realme", "Smartphones", 15999, 12999, 4.1, 2510),
    ("iQOO 12 5G (Alpha, 12GB/256GB)", "iQOO", "Smartphones", 52999, 45999, 4.5, 1342),
    ("iQOO Neo 9 Pro 5G (Conqueror Black, 8GB/256GB)", "iQOO", "Smartphones", 34999, 30999, 4.4, 1789),
    ("iQOO Z9 5G (Brushed Green, 8GB/128GB)", "iQOO", "Smartphones", 19999, 16999, 4.3, 4102),
    # ── Laptops ─────────────────────────────────────────────────────────
    ("HP Pavilion 15 (13th Gen Intel Core i5/16GB/512GB SSD)", "HP", "Laptops", 85990, 71990, 4.3, 980),
    ("HP Victus 15 Gaming (i5/16GB/512GB + RTX 3050)", "HP", "Laptops", 89990, 74990, 4.4, 1240),
    ("HP 15s (12th Gen Intel Core i3/8GB/512GB SSD)", "HP", "Laptops", 45990, 38990, 4.0, 2210),
    ("Dell Inspiron 15 3520 (i5/16GB/512GB SSD)", "Dell", "Laptops", 80990, 66990, 4.2, 856),
    ("Dell XPS 13 9340 (Intel Core Ultra 7/16GB/512GB)", "Dell", "Laptops", 129990, 109990, 4.6, 310),
    ("Dell Latitude 3440 (i5/8GB/256GB SSD)", "Dell", "Laptops", 74990, 59990, 4.1, 420),
    ("Lenovo IdeaPad Slim 5 (Ryzen 7/16GB/512GB)", "Lenovo", "Laptops", 84990, 69990, 4.3, 765),
    ("Lenovo LOQ 15 (i5/16GB/512GB + RTX 4050)", "Lenovo", "Laptops", 84990, 73990, 4.4, 1330),
    ("Lenovo ThinkPad E14 Gen 5 (i5/16GB/512GB)", "Lenovo", "Laptops", 94990, 78990, 4.5, 540),
    ("ASUS Vivobook 16 (Ryzen 7/16GB/512GB)", "ASUS", "Laptops", 72990, 59990, 4.3, 1490),
    ("ASUS TUF Gaming F15 (i5/16GB/512GB + RTX 3050)", "ASUS", "Laptops", 94990, 79990, 4.4, 1830),
    ("ASUS Zenbook 14 OLED (Ultra 5/16GB/512GB)", "ASUS", "Laptops", 109990, 89990, 4.5, 610),
    # ── Home Appliances ─────────────────────────────────────────────────
    ("LG 1.5 Ton 5 Star AI Dual Inverter AC (Copper)", "LG", "Home Appliances", 58990, 47990, 4.5, 3120),
    ("LG 7 kg Front Load Washing Machine (Inverter)", "LG", "Home Appliances", 37990, 29990, 4.4, 2100),
    ("LG 43-inch 4K Ultra HD Smart TV", "LG", "Home Appliances", 37990, 29990, 4.3, 1830),
    ("Samsung 1.5 Ton 5 Star Wind Free AC", "Samsung", "Home Appliances", 55990, 45990, 4.4, 2760),
    ("Samsung 8 kg Front Load Washing Machine (EcoBubble)", "Samsung", "Home Appliances", 43990, 33990, 4.4, 1590),
    ("Samsung 55-inch Crystal 4K Ultra HD Smart TV", "Samsung", "Home Appliances", 68990, 54990, 4.3, 1240),
    ("Bosch 6 kg Front Load Washing Machine (ActiveWater)", "Bosch", "Home Appliances", 34990, 26990, 4.2, 610),
    ("Bosch 13-Place Setting Dishwasher (Series 2)", "Bosch", "Home Appliances", 55990, 43990, 4.3, 480),
    ("Voltas 1.5 Ton 3 Star Split AC (Copper, 2025 Model)", "Voltas", "Home Appliances", 49990, 38990, 4.2, 3450),
    ("Voltas 1.5 Ton 3 Star Window AC (Copper)", "Voltas", "Home Appliances", 38990, 29990, 4.0, 1290),
]

# Realistic Indian marketplace sellers + delivery lines.
SELLERS = {
    "Smartphones": [("RetailNet", "Free delivery by Tomorrow"), ("SuperComNet", "Free delivery in 2 days")],
    "Laptops": [("CompuGiga", "Free delivery by Tomorrow"), ("Vedant Retail", "Free delivery in 3 days")],
    "Home Appliances": [("ConnectShop", "Free installation + delivery in 3 days"), ("SuperComNet", "Free delivery in 4 days")],
}

# ─────────────────────────────────────────────────────────────────────────
# Review bank: (text, star_rating, label, categories)
# `categories` restricts where a review may appear:
#   "smartphones" | "laptops" | "appliances" | "all"
# Keeps laptop talk (keyboard/hinge) out of phone reviews, etc.
# ─────────────────────────────────────────────────────────────────────────
REVIEW_BANK = [
    ("Battery backup is really good, easily one full day with moderate usage. Value for money at this price.", 4.5, "positive", "smartphones"),
    ("Camera takes sharp pictures in daylight but struggles in low light. Overall satisfied.", 3.5, "neutral", "smartphones"),
    ("The phone heats up while charging, but performance is smooth otherwise. No lag at all.", 3.5, "neutral", "smartphones"),
    ("Got this during the Big Billion Days at the best price I have ever seen. Absolutely superb!", 5.0, "positive", "all"),
    ("Delivery took 4 days extra to reach my Tier-2 city. Product is fine though.", 3.0, "negative", "all"),
    ("Display is stunning and the 120Hz refresh feels buttery smooth. Totally worth it.", 5.0, "positive", "smartphones"),
    ("After-sales service is pathetic, they took over a week to respond to my complaint.", 1.5, "negative", "all"),
    ("Good phone for daily use, but battery drains fast after the recent software update.", 2.5, "negative", "smartphones"),
    ("Decent for the price. Not a gaming beast but handles casual games without issues.", 4.0, "neutral", "smartphones"),
    ("Received a sealed box with proper packaging. Very happy with this purchase.", 4.5, "positive", "all"),
    ("Excellent build quality, keyboard is comfortable for long typing sessions.", 4.5, "positive", "laptops"),
    ("Fan is audible under heavy load but the cooling performance is genuinely good.", 3.5, "neutral", "laptops"),
    ("Screen brightness is average, tough to use outdoors. Otherwise a solid machine.", 3.0, "neutral", "laptops"),
    ("Great value laptop for college students, battery easily lasts a full day of classes.", 4.5, "positive", "laptops"),
    ("Unit arrived with a minor scratch, packaging was poor. Seller arranged a partial refund.", 2.5, "negative", "all"),
    ("Boots in seconds and handles my coding workload easily. Very fast machine.", 5.0, "positive", "laptops"),
    ("Hinge feels flimsy after two months of use. Concerned about long-term durability.", 2.0, "negative", "laptops"),
    ("No issues so far, does everything I need for browsing and office work.", 4.0, "neutral", "laptops"),
    ("Great festive offer, bought it cheaper than the local offline store.", 5.0, "positive", "all"),
    ("Warranty claim experience was painful and slow. Hope I never need it again.", 2.0, "negative", "all"),
    ("Cooling is powerful even in peak summer. Best purchase of the year.", 5.0, "positive", "appliances"),
    ("Installation was delayed by two days but the unit works brilliantly.", 3.5, "neutral", "appliances"),
    ("A bit noisy at full power, acceptable at low speed. Good value overall.", 3.0, "neutral", "appliances"),
    ("Energy efficient, my electricity bill actually came down. Very satisfied.", 5.0, "positive", "appliances"),
    ("Unit had a dented panel, but the seller arranged a quick replacement.", 4.0, "positive", "appliances"),
    ("Service centre is far from my area, a small issue took a week to fix.", 2.5, "negative", "all"),
    ("Works exactly as described, solid value for the money paid.", 4.5, "positive", "all"),
    ("The app setup was easy and the smart features are basic but useful.", 4.0, "neutral", "appliances"),
    ("Compressor is a little loud during peak cooling, otherwise fine.", 3.5, "neutral", "appliances"),
    ("Great deal during the Great Indian Festival sale. Highly recommended.", 5.0, "positive", "all"),
]

CATEGORY_TAG = {"Smartphones": "smartphones", "Laptops": "laptops", "Home Appliances": "appliances"}

CATEGORY_TAG = {"Smartphones": "smartphones", "Laptops": "laptops", "Home Appliances": "appliances"}


# ─────────────────────────────────────────────────────────────────────────
# Lexicon fallback (mirrors app/services/ai_sentiment.py so seeds are
# consistent with what the API would compute without an OpenAI key).
# ─────────────────────────────────────────────────────────────────────────
POSITIVE = {"good", "great", "best", "superb", "excellent", "happy", "satisfied", "solid", "love", "value", "fast", "sharp", "worth", "amazing", "awesome", "recommend"}
NEGATIVE = {"bad", "slow", "delay", "heats", "pathetic", "flimsy", "painful", "scratch", "poor", "late", "drains", "loud", "issue", "struggles"}


def sentiment_of(text: str) -> tuple:
    words = set(text.lower().replace(",", " ").replace(".", " ").split())
    score = sum(1 for w in words & POSITIVE) - sum(1 for w in words & NEGATIVE)
    if score > 0:
        return "positive", round(0.6 + min(score, 4) * 0.08, 3)
    if score < 0:
        return "negative", round(0.6 + min(-score, 4) * 0.08, 3)
    return "neutral", 0.5


def slugify(name: str) -> str:
    return "-".join(name.lower().replace("(", "").replace(")", "").split())[:60]


def make_product(index: int, row: tuple) -> dict:
    name, brand, category, mrp, price, rating, rating_count = row
    discount = round((mrp - price) / mrp * 100, 1)
    seller, delivery = SELLERS[category][index % len(SELLERS[category])]
    stock = "In Stock" if index % 7 != 0 else "Only 2 left"
    pid = f"prod-{category.lower().replace(' ', '-')}-{index + 1:03d}"
    return {
        "id": pid,
        "name": name,
        "brand": brand,
        "category": category,
        "image_url": None,  # frontend renders a branded placeholder
        "current_price": price,
        "mrp": mrp,
        "discount_pct": discount,
        "rating": rating,
        "rating_count": rating_count,
        "review_count": 0,  # filled after reviews are generated
        "seller": seller,
        "delivery_estimate": delivery,
        "stock_status": stock,
        "is_active": True,
    }


def make_reviews(product: dict, rng: random.Random) -> list:
    """Pick 5-8 reviews appropriate to the product's category."""
    tag = CATEGORY_TAG.get(product["brand"], CATEGORY_TAG.get(product["category"]))
    pool = [r for r in REVIEW_BANK if r[3] in ("all", tag)] or REVIEW_BANK
    n = rng.randint(5, 8)
    chosen = rng.sample(pool, min(n, len(pool)))
    reviews = []
    for i, (text, star, _label, _tag) in enumerate(chosen):
        label, score = sentiment_of(text)
        reviews.append(
            {
                "review_text": text,
                "star_rating": round(star + rng.uniform(-0.3, 0.3), 1),
                "sentiment_label": label,
                "sentiment_score": score,
                "is_synthetic": True,
                "scraped_at": (datetime.now() - timedelta(days=rng.randint(0, 30))).isoformat() + "Z",
            }
        )
    return reviews


def make_price_history(product: dict, rng: random.Random, days: int = 30) -> list:
    """Bootstrap a 30-day price walk whose LAST point equals the current
    price at `now`, so 24h-window queries (movers, sparklines) work on a
    fresh seed before the first scheduler cycle."""
    prices = [product["current_price"]]
    for _ in range(days - 1):
        shock = rng.uniform(-0.04, 0.04)
        nxt = int(prices[-1] * (1 + shock))
        nxt = max(int(product["mrp"] * 0.35), min(product["mrp"], nxt))
        prices.append(nxt)
    prices.reverse()  # oldest → newest
    now = datetime.now()
    return [
        {
            "price": p,
            "recorded_at": (now - timedelta(hours=23 * (days - 1 - i))).isoformat() + "Z",
        }
        for i, p in enumerate(prices)
    ]


def build() -> dict:
    rng = random.Random(2026)
    products = []
    for i, row in enumerate(CATALOGUE):
        product = make_product(i, row)
        reviews = make_reviews(product, rng)
        product["review_count"] = len(reviews)
        product["reviews"] = reviews
        product["price_history"] = make_price_history(product, rng)
        products.append(product)
    return {"generated_at": datetime.now().isoformat() + "Z", "note": "Simulated seed dataset for BazaarPulse", "products": products}


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = build()
    OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(data['products'])} products to {OUT_PATH}")


if __name__ == "__main__":
    main()
