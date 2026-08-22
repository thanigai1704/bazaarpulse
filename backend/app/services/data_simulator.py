"""Real-time market simulator.

WHAT THIS IS
────────────
Flipkart and Amazon.in deploy aggressive anti-bot protection, so direct
scraping at scale is unreliable and can violate their ToS. BazaarPulse uses
a two-pronged strategy:

  1. SEED DATA  – a realistic Flipkart/Amazon.in-style dataset generated
     offline (see `scripts/generate_seed_data.py`). You can also point this
     at a Kaggle Flipkart/Amazon India CSV by running
     `scripts/load_kaggle_dataset.py`.
  2. SIMULATION – every scheduler cycle this module:
        • perturbs each live price by ±5% (random walk around MRP,
          clipped to a sane floor/ceiling),
        • appends new synthetic reviews (blended from brand-relevant
          review templates),
        • returns typed events that get broadcast over the WebSocket.

This is *clearly* documented as "simulated real-time" for portfolio / demo
purposes. The architecture is identical to what a live scraper would drive —
swapping SCRAPE_MODE=live only changes the producer, not the pipeline.

PRICE WALK
──────────
Prices follow a mean-reverting random walk:
  price[t] = clip(price[t-1] * (1 + gaussian(0, sigma)),
                  mrp * 0.35, mrp)
where sigma=0.02 (~2% typical move, bounded by ±5% per the spec) and a
gentle pull toward mrp*0.9 to keep sale-style discounts believable.
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import numpy as np

from ..config import get_settings
from ..models import Product, Review
from .ai_sentiment import classify_review, clean_text

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_PRICE_SHIFT_PCT = 0.05  # spec: perturb prices by ±5%


# ─── Synthetic review templates (Hinglish-aware, Indian-market tone) ───
_REVIEW_TEMPLATES = {
    "smartphones": [
        ("Battery backup is great, easily lasts a full day with heavy use. Value for money.", 4.5, "pos"),
        ("Camera quality is good for the price but low light is average. Expected more.", 3.5, "neu"),
        ("Phone heats up a bit during charging but overall performance is smooth.", 3.0, "neu"),
        ("Got this on the Big Billion Days deal, best price I have seen. Superb!", 5.0, "pos"),
        ("Delivery was late in my Tier-2 city by 3 days. Product is fine though.", 3.0, "neg"),
        ("Display is stunning, very smooth and responsive. Totally worth it.", 5.0, "pos"),
        ("After-sales service is poor, they took one week to respond. Disappointed.", 1.5, "neg"),
        ("Good phone, average. Battery drains fast after a software update.", 2.5, "neg"),
        ("Overall decent for daily use. Not a gaming phone but handles casual games fine.", 4.0, "neu"),
        ("Received a sealed box, great packaging by the seller. Happy with purchase.", 4.5, "pos"),
    ],
    "laptops": [
        ("Great build quality and the keyboard is comfortable for long typing sessions.", 4.5, "pos"),
        ("Fan noise is noticeable under load but cooling works well.", 3.5, "neu"),
        ("Screen brightness is average, hard to use outdoors. Everything else is fine.", 3.0, "neu"),
        ("Excellent value laptop for college students. Battery lasts the whole day.", 4.5, "pos"),
        ("Seller sent a unit with a minor scratch on the lid. Packaging was poor.", 2.5, "neg"),
        ("The laptop is fast, boots in seconds and handles my coding workload easily.", 5.0, "pos"),
        ("Hinge feels flimsy after two months of use. Worried about longevity.", 2.0, "neg"),
        ("No issues so far, does the job for basic tasks and browsing.", 4.0, "neu"),
        ("Great festive season offer, got it cheaper than offline stores.", 5.0, "pos"),
        ("Customer support for warranty claim was painful to deal with.", 2.0, "neg"),
    ],
    "home_appliances": [
        ("Cooling is powerful even in summer. Best purchase this year.", 5.0, "pos"),
        ("Installation was delayed by two days. Product works well.", 3.5, "neu"),
        ("Noisy while running at full capacity but acceptable at low speed.", 3.0, "neu"),
        ("Energy efficient, noticed lower electricity bills. Very satisfied.", 5.0, "pos"),
        ("Unit arrived with a dented panel, seller arranged replacement quickly.", 4.0, "pos"),
        ("Service center is far from my locality. Minor issue took a week to fix.", 2.5, "neg"),
        ("Works exactly as described. Solid value for the price paid.", 4.5, "pos"),
        ("The smart features are basic but useful. App setup was easy.", 4.0, "neu"),
        ("Compressor is a bit loud during peak cooling. Otherwise fine.", 3.5, "neu"),
        ("Great deal during the Great Indian Festival sale. Recommended.", 5.0, "pos"),
    ],
}

_BRAND_FLAVOR = {
    "Samsung": "Samsung",
    "Xiaomi": "Xiaomi/Redmi",
    "OnePlus": "OnePlus",
    "Realme": "Realme",
    "iQOO": "iQOO",
    "HP": "HP",
    "Dell": "Dell",
    "Lenovo": "Lenovo",
    "ASUS": "ASUS",
    "LG": "LG",
    "Bosch": "Bosch",
    "Voltas": "Voltas",
}


def _templates_for(product: Product) -> List:
    if product.category in _REVIEW_TEMPLATES:
        return _REVIEW_TEMPLATES[product.category]
    return _REVIEW_TEMPLATES["smartphones"]


def _make_synthetic_review(product: Product, seed: int) -> Review:
    """Build a synthetic Review row with a sentiment label attached."""
    rng = random.Random(seed)
    templates = _templates_for(product)
    text, star, _hint = rng.choice(templates)
    text = clean_text(text)

    # Occasionally mention the brand so reviews feel product-specific.
    flavor = _BRAND_FLAVOR.get(product.brand, product.brand)
    if rng.random() < 0.6 and flavor:
        words = text.split()
        insert_at = min(2, len(words))
        words.insert(insert_at, f"({flavor})")
        text = " ".join(words)

    # Star rating jitter within the template band.
    star = max(1.0, min(5.0, star + rng.uniform(-0.5, 0.5)))

    label, score = "neutral", 0.5
    review = Review(
        product_id=product.id,
        review_text=text,
        star_rating=round(star, 1),
        sentiment_label=label,
        sentiment_score=score,
        is_synthetic=True,
        scraped_at=datetime.now(timezone.utc),
    )
    return review


def _perturb_price(product: Product, rng: random.Random) -> dict:
    """Apply the ±5% random-walk step to a product's live price.

    Returns the old/new price and the fractional change so the caller can
    both persist and broadcast a `price_update` event.
    """
    old_price = product.current_price
    sigma = 0.02
    shock = np.clip(rng.gauss(0, sigma), -MAX_PRICE_SHIFT_PCT, MAX_PRICE_SHIFT_PCT)
    # Gentle mean-reversion so prices don't drift to a corner.
    anchor = product.mrp * 0.9
    reversion = (anchor - old_price) / product.mrp * 0.05
    step = shock + reversion

    new_price = int(round(old_price * (1 + step)))
    floor = int(product.mrp * 0.35)
    new_price = max(floor, min(product.mrp, new_price))

    change_pct = (new_price - old_price) / old_price * 100 if old_price else 0.0
    discount_pct = round((product.mrp - new_price) / product.mrp * 100, 1) if product.mrp else 0.0

    return {
        "old_price": old_price,
        "new_price": new_price,
        "change_pct": round(change_pct, 3),
        "discount_pct": discount_pct,
    }


def run_simulation_cycle(
    products: List[Product],
    n_new_reviews_per_product: int = 1,
    review_seed_offset: int = 0,
) -> List[dict]:
    """Execute one full simulation refresh across all active products.

    Returns a list of event dicts (price updates, new reviews) for the
    scheduler to persist + broadcast. Pure function over ORM objects so it
    is easy to unit-test.
    """
    events: List[dict] = []
    rng = random.Random(datetime.now().minute // 5)

    for product in products:
        if not product.is_active:
            continue

        # ── Price move ────────────────────────────────────────────────
        if rng.random() < 0.85:  # not every product moves every cycle
            move = _perturb_price(product, rng)
            product.current_price = move["new_price"]
            product.discount_pct = move["discount_pct"]
            product.last_updated = datetime.now(timezone.utc)
            events.append({"type": "price_update", "product": product, "move": move})

        # ── Synthetic reviews ─────────────────────────────────────────
        for i in range(n_new_reviews_per_product):
            review = _make_synthetic_review(
                product, seed=review_seed_offset + product.id.__hash__() + i
            )
            # Attach sentiment via rule-based or LLM path.
            label, score = _run_sync(classify_review(review.review_text))
            review.sentiment_label = label
            review.sentiment_score = score
            events.append({"type": "new_review", "review": review})

    return events


def _run_sync(coro):
    """Run an async coroutine from the sync simulation cycle."""
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def build_price_history_from_scratch(product: Product, points: int = 20) -> List[int]:
    """Bootstrap a plausible 30-day-looking price history for a seed product
    that has no history yet (used on first seed)."""
    rng = random.Random(product.id.__hash__())
    prices = [product.current_price]
    for _ in range(points - 1):
        shock = np.clip(rng.gauss(0, 0.015), -0.05, 0.05)
        nxt = int(prices[-1] * (1 + shock))
        prices.append(max(int(product.mrp * 0.35), min(product.mrp, nxt)))
    # walk forward, oldest first
    return list(reversed(prices))
