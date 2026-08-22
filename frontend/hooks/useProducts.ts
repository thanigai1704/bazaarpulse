"use client";

import { useCallback, useMemo } from "react";

import { useApi } from "./useApi";
import { api } from "@/lib/api";
import type { Product, ProductListResponse, SentimentLabel } from "@/lib/types";
import { useLiveUpdates } from "./useLiveUpdates";

export interface ProductFilters {
  category?: string;
  brand?: string;
  minPrice?: number;
  maxPrice?: number;
  sentiment?: SentimentLabel;
  sortBy?: string;
}

/** Products list, live-merged with WebSocket price updates. */
export function useProducts(filters: ProductFilters) {
  const key = JSON.stringify(filters);
  const { data, error, loading, refresh } = useApi<ProductListResponse>(
    () =>
      api.products({
        category: filters.category || undefined,
        brand: filters.brand || undefined,
        minPrice: filters.minPrice,
        maxPrice: filters.maxPrice,
        sentiment: filters.sentiment,
        sortBy: filters.sortBy,
      }),
    [key],
  );

  // Merge live price pushes into the listing.
  const { latestByProduct, connected } = useLiveUpdates();

  const products = useMemo<Product[]>(() => {
    if (!data) return [];
    return data.products.map((p) => {
      const update = latestByProduct[p.id];
      if (!update) return p;
      return {
        ...p,
        current_price: update.payload.current_price,
        discount_pct: update.payload.discount_pct,
        last_updated: update.payload.last_updated,
        price_change_24h: update.payload.price_change_pct,
        price_trend: p.price_trend.length ? [...p.price_trend.slice(-19), update.payload.current_price] : [update.payload.current_price],
      };
    });
  }, [data, latestByProduct]);

  const refreshOnLive = useCallback(() => {
    refresh();
  }, [refresh]);

  return {
    products,
    total: data?.total ?? 0,
    error,
    loading,
    connected,
    refresh: refreshOnLive,
  };
}
