/** API types mirroring backend Pydantic schemas. */

export type SentimentLabel = "positive" | "negative" | "neutral";

export interface Product {
  id: string;
  name: string;
  brand: string;
  category: string;
  image_url: string | null;
  current_price: number;
  mrp: number;
  discount_pct: number;
  rating: number;
  rating_count: number;
  seller: string;
  delivery_estimate: string;
  stock_status: string;
  last_updated: string;
  price_change_24h: number;
  price_trend: number[];
  sentiment_label?: SentimentLabel;
  data_source?: "live" | "simulated" | "seed";
}

export interface PricePoint {
  price: number;
  recorded_at: string;
}

export interface ProductDetail extends Product {
  price_history: PricePoint[];
  sentiment: { positive: number; negative: number; neutral: number };
  reviews: ReviewItem[];
}

export interface ProductListResponse {
  products: Product[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReviewItem {
  id: number;
  review_text: string;
  star_rating: number;
  sentiment_label: SentimentLabel;
  sentiment_score: number;
  is_synthetic: boolean;
  scraped_at: string;
}

export interface ProductInsight {
  product_id: string;
  ai_summary: string;
  keywords: string[];
  generated_at: string;
}

export interface MoverItem {
  product_id: string;
  name: string;
  brand: string;
  category: string;
  old_price: number;
  new_price: number;
  change_pct: number;
  image_url: string | null;
}

export interface TrendingInsights {
  biggest_drops: MoverItem[];
  biggest_rises: MoverItem[];
}

export interface SentimentLeader {
  product_id: string;
  name: string;
  brand: string;
  sentiment_score: number;
  sentiment_label: SentimentLabel;
  positive_share: number;
  image_url: string | null;
}

export interface KpiSnapshot {
  products_tracked: number;
  avg_sentiment_score: number;
  avg_sentiment_label: SentimentLabel;
  biggest_drop_24h: MoverItem | null;
  last_synced: string | null;
}

export interface MarketSummary {
  period_label: string;
  summary_text: string;
  movers_json: { product_id: string; name: string; change_pct: number }[];
  generated_at: string;
}

/** WebSocket live events pushed by /ws/live-updates. */
export type LiveEventType =
  | "price_update"
  | "new_review"
  | "insight_updated"
  | "sync_complete"
  | "market_summary"
  | "hello"
  | "pong";

export interface LiveEvent {
  type: LiveEventType;
  occurred_at: string;
  payload: Record<string, unknown>;
}

export interface PriceUpdateEvent {
  type: "price_update";
  occurred_at: string;
  payload: {
    product_id: string;
    name: string;
    brand: string;
    category: string;
    current_price: number;
    mrp: number;
    discount_pct: number;
    price_change_pct: number;
    last_updated: string;
    image_url: string | null;
  };
}

export interface SortOption {
  value: string;
  label: string;
}
