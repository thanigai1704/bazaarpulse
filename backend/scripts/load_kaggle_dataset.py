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
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import PriceHistory, Product  # noqa: E402
from app.services.price_formatter import parse_price  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_NAME_COLS = ["product_name", "name", "title", "product_title"]
_PRICE_COLS = ["current_price", "price", "selling_price", "sale_price"]
_MRP_COLS = ["mrp", "original_price", "retail_price", "list_price"]
_RATING_COLS = ["rating", "product_rating", "star_rating", "average_rating"]
_RATING_COUNT_COLS = ["rating_count", "number_of_ratings", "ratings"]
_REVIEW_COUNT_COLS = ["review_count", "number_of_reviews", "reviews"]


def _pick_col(df: pd.DataFrame, candidates: list) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def clean_and_load(csv_path: str, category: str = "Other") -> int:
    df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
    logger.info("Raw rows: %d", len(df))

    name_col = _pick_col(df, _NAME_COLS)
    price_col = _pick_col(df, _PRICE_COLS)
    mrp_col = _pick_col(df, _MRP_COLS)
    rating_col = _pick_col(df, _RATING_COLS)
    rating_count_col = _pick_col(df, _RATING_COUNT_COLS)
    review_count_col = _pick_col(df, _REVIEW_COUNT_COLS)
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
    cat_col = "category" if "category" in df.columns else None

    db = SessionLocal()
    loaded = 0
    now = datetime.now(timezone.utc)
    try:
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
            cat = str(row[cat_col]).strip() if cat_col and pd.notna(row[cat_col]) else category
            product_id = f"kaggle-{abs(hash(name)) % 999999}"

            product = db.query(Product).filter(Product.name == name).first()
            if product is None:
                product = Product(
                    id=product_id,
                    name=name[:300],
                    brand=brand[:80],
                    category=cat[:80],
                    image_url=None,
                    current_price=price,
                    mrp=mrp,
                    discount_pct=round((mrp - price) / mrp * 100, 1),
                    rating=rating,
                    rating_count=rating_count,
                    review_count=review_count,
                    seller="",
                    delivery_estimate="",
                    stock_status="In Stock",
                    data_source="seed",
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
        return loaded
    finally:
        db.close()


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
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    n = clean_and_load(args.csv, args.category)
    print(f"Done — {n} products imported.")


if __name__ == "__main__":
    main()
