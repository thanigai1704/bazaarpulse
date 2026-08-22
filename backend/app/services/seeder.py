"""Database seeder: loads the generated seed dataset into the DB.

Shared by:
  - scripts/seed_db.py  (manual CLI invocation)
  - app.main startup    (automatic when RESEED_ON_START=true or DB empty)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import PriceHistory, Product, Review

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "seed_products.json"


def _parse_dt(value: str | datetime) -> datetime:
    """Coerce an ISO-8601 string (from the seed JSON) into a datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seed_from_json(db: Session, path: Path | str | None = None) -> int:
    """Idempotent upsert of the seed catalogue. Returns product count loaded."""
    path = Path(path) if path else SEED_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Seed file not found at {path}. Run `python scripts/generate_seed_data.py` first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for p in data["products"]:
        product = db.query(Product).filter(Product.id == p["id"]).first()
        if product is None:
            product = Product(
                id=p["id"],
                name=p["name"],
                brand=p["brand"],
                category=p["category"],
                image_url=p.get("image_url"),
                current_price=p["current_price"],
                mrp=p["mrp"],
                discount_pct=p["discount_pct"],
                rating=p["rating"],
                rating_count=p["rating_count"],
                review_count=p["review_count"],
                seller=p["seller"],
                delivery_estimate=p["delivery_estimate"],
                stock_status=p.get("stock_status", "In Stock"),
                data_source="simulated",  # upgraded to "live" on first live scrape
                is_active=True,
                last_updated=datetime.now(timezone.utc),
            )
            db.add(product)
            count += 1

        # Price history (only if this product has none yet).
        existing_history = (
            db.query(PriceHistory)
            .filter(PriceHistory.product_id == p["id"])
            .count()
        )
        if existing_history == 0:
            for point in p.get("price_history", []):
                db.add(
                    PriceHistory(
                        product_id=p["id"],
                        price=point["price"],
                        recorded_at=_parse_dt(point["recorded_at"]),
                    )
                )

        # Reviews (only if none yet).
        existing_reviews = (
            db.query(Review).filter(Review.product_id == p["id"]).count()
        )
        if existing_reviews == 0:
            for r in p.get("reviews", []):
                db.add(
                    Review(
                        product_id=p["id"],
                        review_text=r["review_text"],
                        star_rating=r["star_rating"],
                        sentiment_label=r["sentiment_label"],
                        sentiment_score=r["sentiment_score"],
                        is_synthetic=r.get("is_synthetic", True),
                        scraped_at=_parse_dt(r["scraped_at"]),
                    )
                )
    db.commit()
    logger.info("Seeded %d products from %s", count, path)
    return count


def seed_if_empty(db: Session) -> bool:
    """Seed automatically when the products table is empty (first boot)."""
    if db.query(Product).count() == 0:
        try:
            seed_from_json(db)
            return True
        except FileNotFoundError:
            logger.warning("No seed file found — skipping auto-seed.")
    return False
