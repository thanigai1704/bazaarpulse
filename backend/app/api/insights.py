"""REST endpoints for market insights: movers, sentiment leaders, AI summary."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MarketSummary, Product, ProductInsight, Review
from ..schemas import (
    KpiSnapshot,
    MarketSummaryOut,
    MoverItem,
    SentimentLeader,
    TrendingInsights,
)
from .products import kpi_snapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/insights", tags=["insights"])


def _movers(db: Session, hours: int = 24) -> dict:
    """Per-product price delta, comparing the first vs last recorded price
    within the window. Falls back to the two most recent rows overall when a
    fresh seed has fewer than 2 points inside the window."""
    from ..models import PriceHistory

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.recorded_at >= cutoff)
        .order_by(PriceHistory.recorded_at.asc())
        .all()
    )
    by_product: dict[str, list] = {}
    for r in rows:
        by_product.setdefault(r.product_id, []).append(r.price)

    # Fallback: latest two rows per product (works on a fresh seed).
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

    drops, rises = [], []
    for pid, prices in by_product.items():
        if len(prices) < 2:
            continue
        first, last = prices[0], prices[-1]
        if first == 0:
            continue
        change = round((last - first) / first * 100, 2)
        product = db.query(Product).filter(Product.id == pid).first()
        if not product:
            continue
        item = MoverItem(
            product_id=pid,
            name=product.name,
            brand=product.brand,
            category=product.category,
            old_price=first,
            new_price=last,
            change_pct=change,
            image_url=product.image_url,
        )
        if change <= 0:
            drops.append(item)
        else:
            rises.append(item)

    drops.sort(key=lambda m: m.change_pct)  # most negative first
    rises.sort(key=lambda m: m.change_pct, reverse=True)
    return {
        "biggest_drops": drops[:5],
        "biggest_rises": rises[:5],
    }


@router.get("/trending", response_model=TrendingInsights)
def trending_insights(hours: int = 24, db: Session = Depends(get_db)):
    """Top 5 price drops and top 5 price rises in the window.

    Great for storytelling around Indian festival sales (Big Billion Days,
    Great Indian Festival) — expect clusters of drops during those weeks.
    """
    return TrendingInsights(**_movers(db, hours))


def _sentiment_aggregates(db: Session) -> list:
    """Per-product aggregate sentiment: avg label score, positive share."""
    rows = (
        db.query(
            Review.product_id,
            func.avg(Review.sentiment_score).label("avg_score"),
            func.count(Review.id).label("n"),
            func.sum(case((Review.sentiment_label == "positive", 1), else_=0)).label("pos"),
        )
        .group_by(Review.product_id)
        .all()
    )
    products = {p.id: p for p in db.query(Product).all()}
    out = []
    for pid, avg_score, n, pos in rows:
        product = products.get(pid)
        if not product or not n:
            continue
        positive_share = round((pos or 0) / n * 100, 1)
        label = "positive" if avg_score >= 0.6 else "negative" if avg_score <= 0.4 else "neutral"
        out.append(
            SentimentLeader(
                product_id=pid,
                name=product.name,
                brand=product.brand,
                sentiment_score=round(float(avg_score), 3),
                sentiment_label=label,
                positive_share=positive_share,
                image_url=product.image_url,
            )
        )
    return out


@router.get("/sentiment-leaders", response_model=List[SentimentLeader])
def sentiment_leaders(db: Session = Depends(get_db)):
    """Products ranked by AI sentiment this week (best and worst)."""
    leaders = _sentiment_aggregates(db)
    leaders.sort(key=lambda s: s.sentiment_score, reverse=True)
    return leaders


@router.get("/summary", response_model=MarketSummaryOut)
def market_summary(db: Session = Depends(get_db)):
    """Latest AI-generated market summary report card."""
    latest = (
        db.query(MarketSummary)
        .order_by(MarketSummary.generated_at.desc())
        .first()
    )
    if latest:
        return MarketSummaryOut(
            period_label=latest.period_label,
            summary_text=latest.summary_text,
            movers_json=latest.movers_json or [],
            generated_at=latest.generated_at,
        )
    return MarketSummaryOut(
        period_label="cycle",
        summary_text="No summary yet — the first refresh cycle will generate one.",
        movers_json=[],
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/movers", response_model=TrendingInsights)
def movers_shortcut(hours: int = 24, db: Session = Depends(get_db)):
    """Alias for /insights/trending (kept for client convenience)."""
    return TrendingInsights(**_movers(db, hours))


@router.get("/kpis", response_model=KpiSnapshot)
def insights_kpis(db: Session = Depends(get_db)):
    """Dashboard header KPIs (products tracked, sentiment, biggest drop, sync)."""
    return kpi_snapshot(db)
