#!/usr/bin/env python
"""Load a Kaggle "Flipkart/Amazon India" CSV into BazaarPulse.

ALTERNATIVE SEED PATH (per the spec):
If you'd rather use real public datasets instead of the bundled generator,
download one and run:

    python scripts/load_kaggle_dataset.py --csv path/to/flipkart_products.csv

Expected columns (we accept several common spellings):
    product_name / name / title
    retail_price / selling_price / price / mrp
    brand, category, product_rating / rating / star_rating
    rating_count, review_count

Anything unrecognised is logged and skipped; rows are cleaned with Pandas
(₹ removal, Indian comma grouping, missing values, duplicate SKUs).
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import func

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import PriceHistory, Product, ProductInsight, Review  # noqa: E402
from app.services.price_formatter import parse_price  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_NAME_COLS = ["product_name", "name", "title", "product_title"]
_PRICE_COLS = ["current_price", "price", "selling_price", "sale_price", "discounted_price"]
_MRP_COLS = ["mrp", "original_price", "retail_price", "list_price"]
_RATING_COLS = ["rating", "product_rating", "star_rating", "average_rating"]
_RATING_COUNT_COLS = ["rating_count", "number_of_ratings", "ratings"]
_REVIEW_COUNT_COLS = ["review_count", "number_of_reviews", "reviews"]
_CATEGORY_TREE_COLS = ["product_category_tree", "category", "category_tree"]
_IMAGE_COLS = ["image", "image_url", "image_link"]

# The Flipkart dump stores category and image as JSON-encoded lists:
#   product_category_tree = '["Clothing", "Women", "Topwear"]'
#   image                 = '["http://.../1100x1100.jpeg", "http://.../1.jpeg"]'
# Older exports use the "A >> B >> C" breadcrumb form instead.
def _json_list(raw) -> list[str]:
    if raw is None or not isinstance(raw, str):
        return []
    text = raw.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        return [str(x).strip() for x in parsed if isinstance(x, str) and x.strip()]
    return [part.strip() for part in text.split(">>") if part.strip()]


def _root_category(raw, depth: int = 1) -> str | None:
    """Normalise the category tree down to a top-level bucket.

    The dataset nests as  '["Clothing >> Women's Clothing >> Lingerie >> Shorts"]'
    so we unwrap the JSON list, split the breadcrumb and take `depth` (1 = root,
    2 = sub-category). Depth 1 keeps the dashboard usable — the full breadcrumb
    produces thousands of near-duplicate buckets.
    """
    parts = _json_list(raw)
    if not parts:
        return None
    crumbs = [c.strip() for c in parts[0].split(">>") if c.strip()]
    if not crumbs:
        return None
    return crumbs[min(depth, len(crumbs)) - 1]


def _first_image(raw) -> str | None:
    """Pick the highest-resolution image URL from the JSON-encoded list."""
    urls = _json_list(raw)
    if not urls:
        return None
    http_urls = [u for u in urls if u.startswith("http")]
    if not http_urls:
        return None
    # The 1100x1100 variant is the largest; fall back to longest string.
    for candidate in http_urls:
        if "1100x1100" in candidate:
            return candidate
    return max(http_urls, key=len)


def _stable_id(name: str, uniq_id) -> str:
    """Deterministic primary key from the dataset's `uniq_id` (a hex digest).

    Keep the hex as-is — stripping non-digits collapsed distinct hex IDs onto
    the same digit string and broke the UNIQUE constraint.
    """
    if uniq_id is not None and pd.notna(uniq_id):
        cleaned = re.sub(r"[^0-9a-f]", "", str(uniq_id).lower())
        if len(cleaned) >= 16:
            return f"fk-{cleaned}"[:64]
    return f"fk-{hashlib.sha1(name.encode('utf-8')).hexdigest()[:24]}"


def _pick_col(df: pd.DataFrame, candidates: list) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def clean_and_load(
    csv_path: str,
    category: str = "Other",
    data_source: str = "seed",
    replace: bool = False,
    category_depth: int = 1,
    min_category_size: int = 30,
) -> int:
    df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
    logger.info("Raw rows: %d", len(df))

    name_col = _pick_col(df, _NAME_COLS)
    price_col = _pick_col(df, _PRICE_COLS)
    mrp_col = _pick_col(df, _MRP_COLS)
    rating_col = _pick_col(df, _RATING_COLS)
    rating_count_col = _pick_col(df, _RATING_COUNT_COLS)
    review_count_col = _pick_col(df, _REVIEW_COUNT_COLS)
    cat_col = _pick_col(df, _CATEGORY_TREE_COLS)
    image_col = _pick_col(df, _IMAGE_COLS)
    if not name_col or not price_col:
        raise ValueError(f"Could not find name/price columns in {list(df.columns)}")

    df = df.drop_duplicates(subset=[name_col], keep="first")
    # String-normalise numeric price columns → int (handles '₹1,45,999').
    df["__price"] = df[price_col].astype(str).map(parse_price)
    df["__mrp"] = (
        df[mrp_col].astype(str).map(parse_price) if mrp_col else df["__price"]
    )
    df["__mrp"] = df[["__mrp", "__price"]].max(axis=1)
    df = df[df["__price"].notna() & df["__price"] > 0].copy()
    if df.empty:
        raise ValueError("No rows survived price cleaning.")

    brand_col = "brand" if "brand" in df.columns else None
    uniq_col = "uniq_id" if "uniq_id" in df.columns else None

    db = SessionLocal()
    loaded = 0
    now = datetime.now(timezone.utc)
    try:
        if replace:
            # SQLite doesn't enforce ON DELETE CASCADE (no PRAGMA foreign_keys
            # in database.py), so child rows are purged explicitly.
            stale_ids = [r[0] for r in db.query(Product.id).all()]
            if stale_ids:
                for model in (PriceHistory, Review, ProductInsight):
                    (
                        db.query(model)
                        .filter(model.product_id.in_(stale_ids))
                        .delete(synchronize_session=False)
                    )
                removed = (
                    db.query(Product)
                    .delete(synchronize_session=False)
                )
                logger.info(
                    "Wiped %d products + dependents for a clean reload", removed
                )
                db.commit()

        for _, row in df.iterrows():
            name = str(row[name_col]).strip()
            if not name:
                continue
            price = int(row["__price"])
            mrp = int(row["__mrp"])
            rating = _safe_float(row, rating_col)
            rating_count = _safe_int(row, rating_count_col)
            review_count = _safe_int(row, review_count_col)
            brand = str(row[brand_col]).strip() if brand_col and pd.notna(row[brand_col]) else "Unknown"
            cat = (
                _root_category(row[cat_col], depth=category_depth)
                if cat_col and pd.notna(row[cat_col])
                else category
            ) or category
            image = _first_image(row[image_col]) if image_col else None
            product_id = _stable_id(name, row[uniq_col] if uniq_col else None)

            product = db.query(Product).filter(Product.name == name).first()
            if product is None:
                product = Product(
                    id=product_id,
                    name=name[:300],
                    brand=brand[:80],
                    category=cat[:80],
                    image_url=image[:500] if image else None,
                    current_price=price,
                    mrp=mrp,
                    discount_pct=round((mrp - price) / mrp * 100, 1),
                    rating=rating,
                    rating_count=rating_count,
                    review_count=review_count,
                    seller="Flipkart",
                    delivery_estimate="",
                    stock_status="In Stock",
                    data_source=data_source,
                    is_active=True,
                    last_updated=now,
                )
                db.add(product)
                db.add(
                    PriceHistory(
                        product_id=product_id,
                        price=price,
                        recorded_at=now,
                    )
                )
                loaded += 1
        db.commit()
        logger.info("Loaded %d new products from %s", loaded, csv_path)
        if min_category_size > 0:
            _collapse_rare_categories(db, min_category_size)
        return loaded
    finally:
        db.close()


def _collapse_rare_categories(db, min_size: int) -> int:
    """Merge categories with fewer than `min_size` products into 'Other'.

    The dataset's category tree is messy: ~90% of buckets are single-item
    entries (often truncated product names leaking into the tree), which would
    make per-category stats meaningless.
    """
    rare = [
        row[0]
        for row in db.query(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .having(func.count(Product.id) < min_size)
        .all()
    ]
    if not rare:
        return 0
    changed = (
        db.query(Product)
        .filter(Product.category.in_(rare))
        .update({"category": "Other"}, synchronize_session=False)
    )
    db.commit()
    logger.info(
        "Collapsed %d sparse categories (%d products) into 'Other'",
        len(rare),
        changed,
    )
    return changed


def _safe_float(row: pd.Series, col: str | None) -> float:
    if col and col in row and pd.notna(row[col]):
        try:
            return float(str(row[col]).replace(" out of 5", "").strip())
        except ValueError:
            return 0.0
    return 0.0


def _safe_int(row: pd.Series, col: str | None) -> int:
    if col and col in row and pd.notna(row[col]):
        digits = "".join(ch for ch in str(row[col]) if ch.isdigit())
        return int(digits) if digits else 0
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Kaggle e-commerce CSV.")
    parser.add_argument("--csv", required=True, help="Path to the CSV file.")
    parser.add_argument("--category", default="Other", help="Default category.")
    parser.add_argument(
        "--data-source",
        default="seed",
        help="Provenance tag stored on every row (e.g. flipkart_2018).",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Wipe existing products (and price history/reviews/insights) "
        "first — makes re-imports idempotent.",
    )
    parser.add_argument(
        "--category-depth",
        type=int,
        default=1,
        help="1 = root category (Clothing), 2 = sub-category, 0 = full breadcrumb.",
    )
    parser.add_argument(
        "--min-category-size",
        type=int,
        default=30,
        help="Collapse categories with fewer products than this into 'Other'.",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    n = clean_and_load(
        args.csv,
        category=args.category,
        data_source=args.data_source,
        replace=args.replace,
        category_depth=args.category_depth,
        min_category_size=args.min_category_size,
    )
    print(f"Done — {n} products imported.")


if __name__ == "__main__":
    main()
