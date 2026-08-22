"""APScheduler integration.

Every SIMULATION_INTERVAL_MINUTES (default 15) a job:

  1. loads active products,
  2. scrapes live (Flipkart/Amazon.in) when SCRAPE_MODE=live|mixed, else runs
     the simulation cycle (price perturbations + synthetic reviews),
  3. classifies new reviews (OpenAI when key present, else lexicon),
  4. persists price_history rows,
  5. regenerates per-product AI insights + the market summary,
  6. broadcasts every change over the WebSocket in near-real-time.

Production uses AsyncIOScheduler so the job runs on uvicorn's event loop —
WebSocket sends must happen on the loop that owns the connection. DB + AI
work is pushed to a worker thread via asyncio.to_thread so the loop never
blocks on SQLite/Postgres I/O or LLM calls.
"""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import get_settings
from .database import SessionLocal
from .models import MarketSummary, PriceHistory, Product, ProductInsight, Review
from .schemas import PriceUpdatePayload
from .services import ai_sentiment
from .services.data_simulator import run_simulation_cycle
from .services.realtime import manager

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler: AsyncIOScheduler | None = None


def _serialize_product_for_ws(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "image_url": product.image_url,
        "current_price": product.current_price,
        "mrp": product.mrp,
        "discount_pct": product.discount_pct,
        "rating": product.rating,
        "rating_count": product.rating_count,
        "review_count": product.review_count,
        "seller": product.seller,
        "delivery_estimate": product.delivery_estimate,
        "stock_status": product.stock_status,
        "last_updated": product.last_updated.isoformat() if product.last_updated else None,
    }


def refresh_cycle_sync() -> tuple:
    """One full market refresh — DB + AI work only (no WebSocket I/O).

    Production order (SCRAPE_MODE=live / mixed):
        1. scrape Flipkart + Amazon.in for tracked brand/category queries,
        2. upsert scraped rows as data_source="live",
        3. record price_history deltas,
        4. only if the live round produced nothing → run the simulator for
           that cycle (data_source="simulated") so the feed never stalls.

    Returns (events, market_summary_text, products) for the caller to broadcast.
    """
    started = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        products = db.query(Product).filter(Product.is_active.is_(True)).all()
        if not products:
            logger.warning("Refresh cycle skipped: no active products (run seed first).")
            return [], "", []

        logger.info("Refresh cycle started with %d products", len(products))

        live_events: list = []
        if settings.scrape_mode in ("live", "mixed"):
            try:
                live_events = _run_live_round(db)
            except Exception as exc:
                logger.warning("Live round failed (%s) — falling back to simulation.", exc)
                db.rollback()
                live_events = []

        if live_events:
            db.commit()
            summary_text = _market_summary_text(db)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            logger.info(
                "LIVE refresh complete in %.2fs (%d live events)",
                elapsed,
                len(live_events),
            )
            return _serialize_events(live_events), summary_text, len(products)

        # ── Fallback: simulated cycle (offline/demo or blocked scrape) ──
        if settings.scrape_mode == "live":
            logger.warning("Live scrape returned nothing; falling back to simulation for this cycle.")
        events = run_simulation_cycle(products, n_new_reviews_per_product=1)

        for event in events:
            if event["type"] == "price_update":
                product = event["product"]
                move = event["move"]
                product.data_source = "simulated"
                db.add(
                    PriceHistory(
                        product_id=product.id,
                        price=move["new_price"],
                        recorded_at=product.last_updated or datetime.now(timezone.utc),
                    )
                )
                db.add(product)
            elif event["type"] == "new_review":
                db.add(event["review"])

        db.flush()

        # Rotating sample of products gets fresh AI insights each cycle.
        import random

        insight_targets = random.sample(products, min(6, len(products)))
        for product in insight_targets:
            _regenerate_insight(db, product)

        avg_sentiment = _avg_sentiment(db)
        summary_text = _sync(ai_sentiment.generate_market_summary(products, avg_sentiment))
        db.add(
            MarketSummary(
                period_label="cycle",
                summary_text=summary_text,
                movers_json=_top_movers(db, products, hours=24),
                generated_at=datetime.now(timezone.utc),
            )
        )

        db.commit()
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        logger.info("Refresh cycle complete in %.2fs (%d events)", elapsed, len(events))
        return _serialize_events(events), summary_text, len(products)
    except Exception as exc:
        logger.exception("Refresh cycle failed: %s", exc)
        db.rollback()
        return [], "", 0
    finally:
        db.close()


def _serialize_events(events: list) -> list:
    """Convert ORM-touching event dicts into plain JSON-safe dicts so they can
    be broadcast after the DB session closes."""
    out = []
    for event in events:
        if event["type"] == "price_update":
            product, move = event["product"], event["move"]
            out.append(
                {
                    "type": "price_update",
                    "payload": PriceUpdatePayload(
                        product_id=product.id,
                        name=product.name,
                        brand=product.brand,
                        category=product.category,
                        current_price=product.current_price,
                        mrp=product.mrp,
                        discount_pct=product.discount_pct,
                        price_change_pct=move["change_pct"],
                        last_updated=product.last_updated or datetime.now(timezone.utc),
                        image_url=product.image_url,
                    ).model_dump(mode="json"),
                }
            )
        elif event["type"] == "new_review":
            review = event["review"]
            out.append(
                {
                    "type": "new_review",
                    "payload": {
                        "product_id": review.product_id,
                        "review_text": review.review_text[:160],
                        "star_rating": review.star_rating,
                        "sentiment_label": review.sentiment_label,
                        "sentiment_score": review.sentiment_score,
                    },
                }
            )
    return out


def refresh_cycle() -> None:
    """Sync entrypoint (scripts / manual triggers). Broadcasts via a temp loop."""
    events, summary_text, products_count = refresh_cycle_sync()
    if events:
        _sync(_broadcast_cycle_events(events, summary_text, products_count))


async def refresh_cycle_async() -> None:
    """Async entrypoint used by AsyncIOScheduler (runs on the uvicorn loop).

    DB/AI work happens in a worker thread; broadcasts happen on the loop that
    owns the WebSocket connections (thread-safe).
    """
    events, summary_text, products_count = await asyncio.to_thread(refresh_cycle_sync)
    if events:
        await _broadcast_cycle_events(events, summary_text, products_count)


def _run_live_round(db) -> list:
    """Scrape both marketplaces and merge results into the DB.

    Returns a list of price_update event dicts for broadcast. Empty list
    means the round was blocked/failed → caller falls back to simulation.
    """
    import asyncio

    from .services.scraper import scrape_live_round

    queries = _build_search_queries()
    raw_items = asyncio.run(scrape_live_round(queries))
    if not raw_items:
        return []

    events: list = []
    for item in raw_items:
        product = _match_or_create_product(db, item)
        if product is None:
            continue
        old_price = product.current_price
        product.current_price = item["current_price"]
        product.mrp = max(item["mrp"], item["current_price"])
        product.discount_pct = round(
            (product.mrp - product.current_price) / product.mrp * 100, 1
        ) if product.mrp else 0.0
        product.rating = item.get("rating") or product.rating
        product.rating_count = item.get("rating_count") or product.rating_count
        product.seller = item.get("seller") or product.seller
        product.delivery_estimate = item.get("delivery_estimate") or product.delivery_estimate
        product.data_source = "live"
        product.last_updated = datetime.now(timezone.utc)

        if product.current_price != old_price:
            db.add(
                PriceHistory(
                    product_id=product.id,
                    price=product.current_price,
                    recorded_at=product.last_updated,
                )
            )
            change_pct = (product.current_price - old_price) / old_price * 100 if old_price else 0.0
            events.append(
                {
                    "type": "price_update",
                    "product": product,
                    "move": {
                        "old_price": old_price,
                        "new_price": product.current_price,
                        "change_pct": round(change_pct, 3),
                        "discount_pct": product.discount_pct,
                    },
                }
            )

    logger.info("Live round merged %d items (%d price moves)", len(raw_items), len(events))
    return events


_BRAND_CATEGORY_MAP = {
    "samsung": "Smartphones", "xiaomi": "Smartphones", "redmi": "Smartphones",
    "oneplus": "Smartphones", "realme": "Smartphones", "iqoo": "Smartphones",
    "hp": "Laptops", "dell": "Laptops", "lenovo": "Laptops", "asus": "Laptops",
    "lg": "Home Appliances", "bosch": "Home Appliances", "voltas": "Home Appliances",
}

_BRAND_DISPLAY = {
    "samsung": "Samsung", "xiaomi": "Xiaomi", "redmi": "Xiaomi",
    "oneplus": "OnePlus", "realme": "Realme", "iqoo": "iQOO",
    "hp": "HP", "dell": "Dell", "lenovo": "Lenovo", "asus": "ASUS",
    "lg": "LG", "bosch": "Bosch", "voltas": "Voltas",
}


def _infer_brand_category(name: str) -> tuple:
    lowered = name.lower()
    for key, brand in _BRAND_DISPLAY.items():
        if key in lowered:
            return brand, _BRAND_CATEGORY_MAP[key]
    return "Unknown", "Other"


def _match_or_create_product(db, item: dict):
    """Match a scraped row to an existing product by name similarity, else
    create one. Returns None if the item is unusable."""
    from difflib import SequenceMatcher

    name = (item.get("name") or "").strip()
    if not name or not item.get("current_price"):
        return None
    brand, category = _infer_brand_category(name)

    existing = db.query(Product).filter(Product.name == name).first()
    if existing:
        return existing

    # Fuzzy match against existing products (scraped names drift in format).
    seed = db.query(Product).all()
    best = None
    best_score = 0.55
    for candidate in seed:
        score = SequenceMatcher(None, name.lower(), candidate.name.lower()).ratio()
        if score > best_score and candidate.brand == brand:
            best, best_score = candidate, score
    if best is not None:
        return best

    product = Product(
        id=f"live-{len(name) % 997}-{abs(hash(name)) % 100000}",
        name=name[:300],
        brand=brand,
        category=category,
        image_url=None,
        current_price=item["current_price"],
        mrp=max(item.get("mrp") or item["current_price"], item["current_price"]),
        discount_pct=0.0,
        rating=item.get("rating") or 0.0,
        rating_count=item.get("rating_count") or 0,
        review_count=0,
        seller=item.get("seller") or "",
        delivery_estimate=item.get("delivery_estimate") or "",
        stock_status="In Stock",
        data_source="live",
        last_updated=datetime.now(timezone.utc),
    )
    db.add(product)
    db.flush()
    return product


def _build_search_queries() -> list:
    """Product queries per brand/category for the live scrape round."""
    return [
        "samsung galaxy mobile",
        "xiaomi redmi note",
        "oneplus mobile 5g",
        "realme 5g mobile",
        "iqoo 5g mobile",
        "hp laptop intel i5",
        "dell laptop 16gb",
        "lenovo laptop ryzen",
        "asus laptop i5",
        "lg inverter ac 1.5 ton",
        "samsung washing machine 8kg",
        "bosch dishwasher",
        "voltas ac 1.5 ton",
    ]


def _regenerate_insight(db, product) -> None:
    """(Re)compute AI summary + keywords for one product."""
    review_texts = [
        r.review_text
        for r in db.query(Review)
        .filter(Review.product_id == product.id)
        .order_by(Review.scraped_at.desc())
        .limit(40)
        .all()
    ]
    summary, keywords = _sync(ai_sentiment.summarize_product(review_texts))
    existing = (
        db.query(ProductInsight)
        .filter(ProductInsight.product_id == product.id)
        .first()
    )
    if existing:
        existing.ai_summary = summary
        existing.keywords = keywords
        existing.generated_at = datetime.now(timezone.utc)
    else:
        db.add(
            ProductInsight(
                product_id=product.id,
                ai_summary=summary,
                keywords=keywords,
                generated_at=datetime.now(timezone.utc),
            )
        )


def _market_summary_text(db) -> str:
    avg = _avg_sentiment(db)
    products = db.query(Product).filter(Product.is_active.is_(True)).all()
    return _sync(ai_sentiment.generate_market_summary(products, avg))


def _avg_sentiment(db) -> float:
    rows = db.query(Review.sentiment_score).all()
    if not rows:
        return 0.5
    return sum(r[0] for r in rows) / len(rows)


def _top_movers(db, products, hours: int) -> list:
    """Last-cycle price movers for the summary card."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for product in products:
        latest = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.product_id == product.id,
                PriceHistory.recorded_at >= cutoff,
            )
            .order_by(PriceHistory.recorded_at.desc())
            .limit(2)
            .all()
        )
        if len(latest) == 2:
            change = round((latest[0].price - latest[1].price) / latest[1].price * 100, 2)
            out.append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "change_pct": change,
                    "price": latest[0].price,
                }
            )
    out.sort(key=lambda m: m["change_pct"])
    return out


async def _broadcast_cycle_events(events: list, market_summary: str, products_count: int) -> None:
    """Push serialized price/review events + sync completion to every client.

    `events` are plain dicts: {"type": ..., "payload": {...}}.
    """
    for event in events:
        await manager.broadcast(event["type"], event["payload"])

    await manager.broadcast(
        "sync_complete",
        {
            "market_summary": market_summary,
            "products_count": products_count,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def _sync(coro):
    """Run an async coroutine from the scheduler's worker thread."""
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def start_scheduler() -> AsyncIOScheduler | None:
    global scheduler
    if scheduler is not None:
        return scheduler

    if not settings.enable_scheduler:
        logger.info("Scheduler disabled via ENABLE_SCHEDULER=false")
        return None

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        refresh_cycle_async,
        trigger=IntervalTrigger(minutes=settings.simulation_interval_minutes),
        id="market_refresh",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started (interval=%d min)",
        settings.simulation_interval_minutes,
    )
    return scheduler


def stop_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
