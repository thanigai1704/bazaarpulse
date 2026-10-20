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

/** GET /analysis — descriptive statistics over the real catalogue. */
export interface AnalysisOverview {
  listings: number;
  categories: number;
  brands: number;
  price_min: number;
  price_median: number;
  price_mean: number;
  price_max: number;
  mean_discount_pct: number;
  median_discount_pct: number;
  total_listings_worth: number;
}

export interface AnalysisDataQuality {
  rating_coverage_pct: number;
  rated_listings: number;
  unrated_listings: number;
  brand_coverage_pct: number;
  duplicate_name_pct: number;
  duplicate_names: number;
  discounted_share_pct: number;
  rated_vs_unrated: {
    rated_mean_price: number | null;
    unrated_mean_price: number | null;
    rated_mean_discount_pct: number | null;
    unrated_mean_discount_pct: number | null;
  };
}

export interface PriceDispersionRow {
  category: string;
  listings: number;
  min: number;
  q25: number;
  median: number;
  q75: number;
  max: number;
  mean: number;
  std: number;
  cv: number | null;
  skewness: number;
  iqr: number;
}

export interface DiscountDepthRow {
  category: string;
  listings: number;
  mean_discount_pct: number;
  median_discount_pct: number;
  p90_discount_pct: number;
  max_discount_pct: number;
  share_discounted_pct: number;
  mean_vs_median_gap: number;
}

export interface BrandConcentration {
  hhi: number;
  interpretation: string;
  top5_share_pct: number;
  top10_share_pct: number;
  pareto_brand_count: number;
  pareto_brand_pct: number;
  top_brands: { brand: string; listings: number; share_pct: number }[];
}

export interface AnalysisCorrelations {
  discount_vs_rating_r: number | null;
  discount_vs_rating_n: number;
  discount_vs_rating_note: string;
  price_vs_discount_r: number | null;
  log_price_vs_rating_r: number | null;
  price_vs_discount_note: string;
}

export interface AnalysisOutliers {
  rule: string;
  outlier_count: number;
  outlier_share_pct: number;
  outlier_median_price: number | null;
  top_outliers: {
    id: string;
    name: string;
    brand: string;
    category: string;
    price: number;
    category_median: number;
    vs_median_x: number;
  }[];
}

export interface MarketAnalysis {
  overview: AnalysisOverview;
  data_quality: AnalysisDataQuality;
  price_dispersion: PriceDispersionRow[];
  discount_depth: DiscountDepthRow[];
  brand_concentration: BrandConcentration;
  correlations: AnalysisCorrelations;
  outliers: AnalysisOutliers;
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
