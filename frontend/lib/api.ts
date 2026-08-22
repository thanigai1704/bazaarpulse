/** Typed API client for the BazaarPulse backend. */

import type {
  KpiSnapshot,
  MarketSummary,
  MoverItem,
  Product,
  ProductDetail,
  ProductInsight,
  ProductListResponse,
  SentimentLeader,
  TrendingInsights,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export interface ProductQuery {
  category?: string;
  brand?: string;
  minPrice?: number;
  maxPrice?: number;
  sentiment?: string;
  sortBy?: string;
  page?: number;
  pageSize?: number;
}

function toQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "" && v !== null) {
      search.set(k, String(v));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${detail.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  products: (q: ProductQuery = {}): Promise<ProductListResponse> =>
    request<ProductListResponse>(
      `/products${toQuery({
        category: q.category,
        brand: q.brand,
        min_price: q.minPrice,
        max_price: q.maxPrice,
        sentiment: q.sentiment,
        sort_by: q.sortBy,
        page: q.page,
        page_size: q.pageSize,
      })}`,
    ),

  product: (id: string): Promise<ProductDetail> => request<ProductDetail>(`/products/${id}`),

  productInsight: (id: string): Promise<ProductInsight> =>
    request<ProductInsight>(`/products/${id}/insight`),

  kpis: (): Promise<KpiSnapshot> => request<KpiSnapshot>(`/insights/kpis`),

  trending: (hours = 24): Promise<TrendingInsights> =>
    request<TrendingInsights>(`/insights/trending${toQuery({ hours })}`),

  movers: (): Promise<{ biggest_drops: MoverItem[]; biggest_rises: MoverItem[] }> =>
    request(`/insights/movers`),

  sentimentLeaders: (): Promise<SentimentLeader[]> =>
    request<SentimentLeader[]>(`/insights/sentiment-leaders`),

  summary: (): Promise<MarketSummary> => request<MarketSummary>(`/insights/summary`),
};
