"""Pydantic response schemas for the REST API and WebSocket payloads."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ─── Products ──────────────────────────────────────────────────────────
class ProductLite(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    image_url: Optional[str] = None
    current_price: int
    mrp: int
    discount_pct: float
    rating: float
    rating_count: int
    seller: str
    delivery_estimate: str
    stock_status: str
    last_updated: datetime

    # Derived, computed by the API layer (not columns).
    price_change_24h: float = 0.0
    price_trend: List[float] = Field(default_factory=list)
    sentiment_label: Optional[str] = None  # latest review label, for list badges


class PricePoint(BaseModel):
    price: int
    recorded_at: datetime


# ─── Sentiment ─────────────────────────────────────────────────────────
class ReviewItem(BaseModel):
    id: int
    review_text: str
    star_rating: float
    sentiment_label: str
    sentiment_score: float
    is_synthetic: bool
    scraped_at: datetime


class SentimentBreakdown(BaseModel):
    positive: float
    negative: float
    neutral: float
    sample_reviews: List[ReviewItem] = Field(default_factory=list)


class ProductDetail(ProductLite):
    price_history: List[PricePoint] = Field(default_factory=list)
    sentiment: SentimentBreakdown = Field(default_factory=SentimentBreakdown)
    reviews: List[ReviewItem] = Field(default_factory=list)


class ProductInsightOut(BaseModel):
    product_id: str
    ai_summary: str
    keywords: List[str]
    generated_at: datetime


# ─── Filters / requests ────────────────────────────────────────────────
class ProductFilters(BaseModel):
    category: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    sort_by: Literal["price_asc", "price_desc", "rating", "discount", "updated"] = "rating"


class ProductListResponse(BaseModel):
    products: List[ProductLite]
    total: int
    page: int
    page_size: int


# ─── Insights ──────────────────────────────────────────────────────────
class MoverItem(BaseModel):
    product_id: str
    name: str
    brand: str
    category: str
    old_price: int
    new_price: int
    change_pct: float
    image_url: Optional[str] = None


class TrendingInsights(BaseModel):
    biggest_drops: List[MoverItem]
    biggest_rises: List[MoverItem]


class SentimentLeader(BaseModel):
    product_id: str
    name: str
    brand: str
    sentiment_score: float
    sentiment_label: str
    positive_share: float
    image_url: Optional[str] = None


class MarketSummaryOut(BaseModel):
    period_label: str
    summary_text: str
    movers_json: List[dict]
    generated_at: datetime


# ─── Dashboard KPIs ────────────────────────────────────────────────────
class KpiSnapshot(BaseModel):
    products_tracked: int
    avg_sentiment_score: float
    avg_sentiment_label: str
    biggest_drop_24h: Optional[MoverItem] = None
    last_synced: Optional[datetime] = None


# ─── WebSocket ─────────────────────────────────────────────────────────
class LiveUpdateEvent(BaseModel):
    type: Literal[
        "price_update",
        "new_review",
        "insight_updated",
        "sync_complete",
        "market_summary",
        "hello",
    ]
    occurred_at: datetime
    payload: dict


class PriceUpdatePayload(BaseModel):
    product_id: str
    name: str
    brand: str
    category: str
    current_price: int
    mrp: int
    discount_pct: float
    price_change_pct: float
    last_updated: datetime
    image_url: Optional[str] = None
