-- ─────────────────────────────────────────────────────────────────────
-- BazaarPulse — Database schema (PostgreSQL / Supabase)
-- Apply with: psql $DATABASE_URL -f 001_create_tables.sql
-- (The FastAPI app auto-creates these tables locally via SQLAlchemy;
--  this file is the canonical schema for Supabase/PostgreSQL.)
-- ─────────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Products: live snapshot of each tracked SKU.
CREATE TABLE IF NOT EXISTS products (
    id                VARCHAR(64) PRIMARY KEY,
    name              VARCHAR(300) NOT NULL,
    brand             VARCHAR(80)  NOT NULL,
    category          VARCHAR(80)  NOT NULL,
    image_url         VARCHAR(500),
    current_price     INTEGER      NOT NULL,                -- ₹, Indian grouping
    mrp               INTEGER      NOT NULL,
    discount_pct      DOUBLE PRECISION DEFAULT 0,
    rating            DOUBLE PRECISION DEFAULT 0,           -- /5
    rating_count      INTEGER      DEFAULT 0,
    review_count      INTEGER      DEFAULT 0,
    seller            VARCHAR(120) DEFAULT '',
    delivery_estimate VARCHAR(120) DEFAULT '',
    stock_status      VARCHAR(40)  DEFAULT 'In Stock',
    data_source       VARCHAR(20)  DEFAULT 'simulated',     -- live | simulated
    is_active         BOOLEAN      DEFAULT TRUE,
    last_updated      TIMESTAMPTZ  DEFAULT now()
);

-- Price history: time-series for trend charts.
CREATE TABLE IF NOT EXISTS price_history (
    id          BIGSERIAL PRIMARY KEY,
    product_id  VARCHAR(64) NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price       INTEGER     NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_price_history_product_time
    ON price_history (product_id, recorded_at DESC);

-- Reviews: raw text + AI sentiment labels.
CREATE TABLE IF NOT EXISTS reviews (
    id              BIGSERIAL PRIMARY KEY,
    product_id      VARCHAR(64) NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    review_text     TEXT        NOT NULL,
    star_rating     DOUBLE PRECISION DEFAULT 0,
    sentiment_label VARCHAR(20) DEFAULT 'neutral',          -- positive|negative|neutral
    sentiment_score DOUBLE PRECISION DEFAULT 0,             -- confidence 0..1
    is_synthetic    BOOLEAN     DEFAULT FALSE,
    scraped_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews (product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment ON reviews (sentiment_label);

-- Per-product AI insight (one-line summary + keyword tags).
CREATE TABLE IF NOT EXISTS product_insights (
    product_id   VARCHAR(64) PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    ai_summary   TEXT,
    keywords     JSONB DEFAULT '[]',
    generated_at TIMESTAMPTZ DEFAULT now()
);

-- Market-wide AI summaries per cycle.
CREATE TABLE IF NOT EXISTS market_summaries (
    id            BIGSERIAL PRIMARY KEY,
    period_label  VARCHAR(40) DEFAULT 'cycle',
    summary_text  TEXT,
    movers_json   JSONB DEFAULT '[]',
    generated_at  TIMESTAMPTZ DEFAULT now()
);

-- Convenience view: latest price per product (for fast movers queries).
CREATE OR REPLACE VIEW v_latest_prices AS
SELECT DISTINCT ON (ph.product_id)
       ph.product_id,
       ph.price,
       ph.recorded_at
FROM price_history ph
ORDER BY ph.product_id, ph.recorded_at DESC;
