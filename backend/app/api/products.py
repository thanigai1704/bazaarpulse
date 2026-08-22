"""REST endpoints for products: listing, filtering, detail, KPIs."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, ProductInsight, Review
from ..schemas import (
    KpiSnapshot,
    MoverItem,
    PricePoint,
    ProductDetail,
    ProductInsightOut,
    ProductLite,
    ProductListResponse,
    ReviewItem,
    SentimentBreakdown,
)
from ..services.price_formatter import format_inr

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["products"])

VALID_SORTS = {"price_asc", "price_desc", "rating", "discount", "updated"}
_ORDER_CLAUSES = {
    "price_asc": Product.current_price.asc(),
    "price_desc": Product.current_price.desc(),
    "rating": Product.rating.desc(),
    "discount": Product.discount_pct.desc(),
    "updated": Product.last_updated.desc(),
}


def _trend_prices(db: Session, product_id: str, days: int = 14) -> list:
    """Last `days` of prices, oldest first, for sparklines."""
    from ..models import PriceHistory

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id, PriceHistory.recorded_at >= cutoff)
        .order_by(PriceHistory.recorded_at.asc())
        .limit(30)
        .all()
    )
    return [r.price for r in rows]


def _price_change_24h(db: Session, product_id: str) -> float:
    """% price change over the last 24h window."""
    from ..models import PriceHistory

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    window = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id, PriceHistory.recorded_at >= cutoff)
        .order_by(PriceHistory.recorded_at.asc())
        .all()
    )
    if len(window) < 2:
        return 0.0
    first, last = window[0].price, window[-1].price
    if first == 0:
        return 0.0
    return round((last - first) / first * 100, 2)


def to_lite(db: Session, product: Product, sentiment_label: Optional[str] = None) -> ProductLite:
    return ProductLite(
        id=product.id,
        name=product.name,
        brand=product.brand,
        category=product.category,
        image_url=product.image_url,
        current_price=product.current_price,
        mrp=product.mrp,
        discount_pct=product.discount_pct,
        rating=product.rating,
        rating_count=product.rating_count,
        seller=product.seller,
        delivery_estimate=product.delivery_estimate,
        stock_status=product.stock_status,
        last_updated=product.last_updated,
        price_change_24h=_price_change_24h(db, product.id),
        price_trend=_trend_prices(db, product.id),
        sentiment_label=sentiment_label,
    )


def _latest_review_labels(db: Session) -> dict:
    """product_id → sentiment label of its most recent review."""
    latest_rows = (
        db.query(Review.product_id, func.max(Review.scraped_at))
        .group_by(Review.product_id)
        .all()
    )
    result: dict = {}
    for product_id, max_scraped in latest_rows:
        row = (
            db.query(Review.sentiment_label)
            .filter(Review.product_id == product_id, Review.scraped_at == max_scraped)
            .first()
        )
        if row:
            result[product_id] = row[0]
    return result


@router.get("", response_model=ProductListResponse)
def list_products(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    sentiment: Optional[str] = Query(None, pattern="^(positive|negative|neutral)$"),
    sort_by: str = Query("rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List products with Indian-market filters.

    - category / brand        → exact match
    - min_price / max_price   → ₹ range on current_price
    - sentiment               → product whose most recent review mix skews to a label
    - sort_by                 → price_asc|price_desc|rating|discount|updated
    """
    sort_by = sort_by if sort_by in VALID_SORTS else "rating"
    query = db.query(Product).filter(Product.is_active.is_(True))

    if category:
        query = query.filter(Product.category == category)
    if brand:
        query = query.filter(Product.brand == brand)
    if min_price is not None:
        query = query.filter(Product.current_price >= min_price)
    if max_price is not None:
        query = query.filter(Product.current_price <= max_price)

    # Sentiment filter: products whose *latest* review is of that label,
    # or whose aggregate sentiment leans that way when no reviews exist.
    latest_labels = _latest_review_labels(db)
    if sentiment:
        good_ids = {pid for pid, label in latest_labels.items() if label == sentiment}
        matched = [pid for pid in [p.id for p in query.all()] if pid in good_ids]
        query = query.filter(Product.id.in_(matched)) if matched else query.filter(Product.id.in_([]))

    total = query.count()
    products = query.order_by(_ORDER_CLAUSES[sort_by]).offset((page - 1) * page_size).limit(page_size).all()

    return ProductListResponse(
        products=[to_lite(db, p, latest_labels.get(p.id)) for p in products],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Full product detail: latest snapshot + price history + reviews +
    sentiment breakdown + AI insight."""
    from ..models import PriceHistory

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    price_rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at.asc())
        .limit(200)
        .all()
    )
    history = [PricePoint(price=r.price, recorded_at=r.recorded_at) for r in price_rows]

    reviews = (
        db.query(Review)
        .filter(Review.product_id == product_id)
        .order_by(Review.scraped_at.desc())
        .limit(200)
        .all()
    )
    sentiment = _sentiment_breakdown(reviews)

    return ProductDetail(
        **to_lite(db, product, _latest_review_labels(db).get(product_id)).model_dump(),
        price_history=history,
        sentiment=_sentiment_breakdown(reviews),
        reviews=[
            ReviewItem(
                id=r.id,
                review_text=r.review_text,
                star_rating=r.star_rating,
                sentiment_label=r.sentiment_label,
                sentiment_score=r.sentiment_score,
                is_synthetic=r.is_synthetic,
                scraped_at=r.scraped_at,
            )
            for r in reviews
        ],
    )


@router.get("/{product_id}/insight", response_model=ProductInsightOut)
def get_product_insight(product_id: str, db: Session = Depends(get_db)):
    """AI one-liner + keyword tags for a single product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    insight = db.query(ProductInsight).filter(ProductInsight.product_id == product_id).first()
    if not insight:
        return ProductInsightOut(
            product_id=product_id,
            ai_summary="No AI insight generated yet — it is computed on the next refresh cycle.",
            keywords=[],
            generated_at=datetime.now(timezone.utc),
        )
    return ProductInsightOut(
        product_id=product_id,
        ai_summary=insight.ai_summary,
        keywords=insight.keywords or [],
        generated_at=insight.generated_at,
    )


def _sentiment_breakdown(reviews: list) -> dict:
    """Aggregate label shares + recent sample reviews for the donut chart."""
    labels = {"positive": 0, "negative": 0, "neutral": 0}
    for r in reviews:
        labels[r.sentiment_label] = labels.get(r.sentiment_label, 0) + 1
    total = max(1, len(reviews))
    sample = [
        ReviewItem(
            id=r.id,
            review_text=r.review_text,
            star_rating=r.star_rating,
            sentiment_label=r.sentiment_label,
            sentiment_score=r.sentiment_score,
            is_synthetic=r.is_synthetic,
            scraped_at=r.scraped_at,
        )
        for r in reviews[:4]
    ]
    return SentimentBreakdown(
        positive=round(labels["positive"] / total * 100, 1),
        negative=round(labels["negative"] / total * 100, 1),
        neutral=round(labels["neutral"] / total * 100, 1),
        sample_reviews=sample,
    )


def kpi_snapshot(db: Session) -> KpiSnapshot:
    products_tracked = db.query(Product).filter(Product.is_active.is_(True)).count()
    avg_score = round(
        float(db.query(func.avg(Review.sentiment_score)).scalar() or 0.5), 3
    )
    label = (
        "positive"
        if avg_score >= 0.6
        else "negative"
        if avg_score <= 0.4
        else "neutral"
    )
    biggest_drop = None
    drop = _biggest_mover(db, direction="drop", hours=24)
    if drop:
        biggest_drop = MoverItem(**drop)
    last_sync = db.query(func.max(Product.last_updated)).scalar()
    return KpiSnapshot(
        products_tracked=products_tracked,
        avg_sentiment_score=avg_score,
        avg_sentiment_label=label,
        biggest_drop_24h=biggest_drop,
        last_synced=last_sync,
    )


def _biggest_mover(db: Session, direction: str, hours: int) -> Optional[dict]:
    """Largest absolute % price change, preferring the `hours` window but
    falling back to the two latest rows (fresh-seed friendly)."""
    from ..models import PriceHistory

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.recorded_at >= cutoff)
        .order_by(PriceHistory.recorded_at.asc())
        .all()
    )
    by_product: dict = {}
    for r in rows:
        by_product.setdefault(r.product_id, []).append(r.price)
    for pid, prices in list(by_product.items()):
        if len(prices) < 2:
            recent = (
                db.query(PriceHistory)
                .filter(PriceHistory.product_id == pid)
                .order_by(PriceHistory.recorded_at.desc())
                .limit(2)
                .all()
            )
            if len(recent) == 2:
                by_product[pid] = [recent[1].price, recent[0].price]
    best = None
    for pid, prices in by_product.items():
        if len(prices) < 2:
            continue
        change = (prices[-1] - prices[0]) / prices[0] * 100
        if direction == "drop" and change >= 0:
            continue
        if direction == "rise" and change <= 0:
            continue
        if best is None or abs(change) > abs(best["change_pct"]):
            product = db.query(Product).filter(Product.id == pid).first()
            if product:
                best = {
                    "product_id": pid,
                    "name": product.name,
                    "brand": product.brand,
                    "category": product.category,
                    "old_price": prices[0],
                    "new_price": prices[-1],
                    "change_pct": round(change, 2),
                    "image_url": product.image_url,
                }
    return best
