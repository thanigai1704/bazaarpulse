"""BazaarPulse — FastAPI application entrypoint.

Run locally:
    cd backend
    pip install -r requirements.txt
    python scripts/generate_seed_data.py
    python scripts/seed_db.py
    uvicorn app.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
Live WebSocket feed: ws://localhost:8000/ws/live-updates
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api import insights, products
from .config import get_settings
from .database import Base, SessionLocal, engine
from .scheduler import start_scheduler, stop_scheduler
from .services.realtime import manager
from .services.seeder import seed_if_empty

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("bazaarpulse")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, auto-seed on first boot, start the scheduler."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if settings.reseed_on_start:
            from .services.seeder import seed_from_json

            seed_from_json(db)
        else:
            seeded = seed_if_empty(db)
            if seeded:
                logger.info("First boot — auto-seeded catalogue.")
    finally:
        db.close()

    scheduler = start_scheduler()
    if scheduler is None:
        logger.warning("Scheduler not running (ENABLE_SCHEDULER=false). "
                       "Data will stay static until you run refresh_cycle() manually.")
    logger.info(
        "BazaarPulse ready — scrape_mode=%s, interval=%dmin, ws=%s",
        settings.scrape_mode,
        settings.simulation_interval_minutes,
        settings.websocket_path,
    )
    yield
    stop_scheduler()


app = FastAPI(
    title="BazaarPulse API",
    description="Real-time Indian e-commerce price & sentiment intelligence.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parse_cors(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(insights.router)


@app.get("/health")
def health():
    return {"status": "ok", "scrape_mode": settings.scrape_mode, "ws": settings.websocket_path}


@app.websocket("/ws/live-updates")
async def ws_live_updates(websocket: WebSocket):
    """Real-time feed: price moves, new reviews, sync completions, summaries.

    Frontend connects with `new WebSocket("wss://host/ws/live-updates")`
    and receives JSON events with {type, occurred_at, payload}.
    """
    await manager.connect(websocket)
    try:
        await manager.send_hello(websocket)
        while True:
            # Clients can (optionally) send {"action": "ping"}.
            data = await websocket.receive_json()
            if data.get("action") == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


@app.get("/")
def root():
    return {
        "name": "BazaarPulse",
        "docs": "/docs",
        "health": "/health",
        "live_feed": "/ws/live-updates",
        "message": "Simulated real-time market intelligence for the Indian e-commerce market.",
    }
