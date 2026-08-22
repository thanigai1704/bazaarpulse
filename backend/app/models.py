"""SQLAlchemy ORM models mirroring the SQL migration files.

Tables:
    products        – live product snapshot
    price_history   – time-series of prices (trend charts)
    reviews         – customer reviews + AI sentiment labels
    product_insights– per-product AI summary + keyword tags
    market_summaries– periodic AI-generated market-wide summaries
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    brand: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    current_price: Mapped[int] = mapped_column(Integer, nullable=False)
    mrp: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    seller: Mapped[str] = mapped_column(String(120), default="")
    delivery_estimate: Mapped[str] = mapped_column(String(120), default="")
    stock_status: Mapped[str] = mapped_column(String(40), default="In Stock")
    # Where this row's price came from: "live" (scraped) | "simulated"
    data_source: Mapped[str] = mapped_column(String(20), default="simulated", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    insight: Mapped["ProductInsight | None"] = relationship(
        back_populates="product", cascade="all, delete-orphan", uselist=False
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    product: Mapped[Product] = relationship(back_populates="price_history")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    star_rating: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_label: Mapped[str] = mapped_column(
        String(20), default="neutral", index=True
    )
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    product: Mapped[Product] = relationship(back_populates="reviews")


class ProductInsight(Base):
    __tablename__ = "product_insights"

    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    product: Mapped[Product] = relationship(back_populates="insight")


class MarketSummary(Base):
    __tablename__ = "market_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period_label: Mapped[str] = mapped_column(String(40), default="weekly")
    summary_text: Mapped[str] = mapped_column(Text, default="")
    movers_json: Mapped[list] = mapped_column(JSON, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
