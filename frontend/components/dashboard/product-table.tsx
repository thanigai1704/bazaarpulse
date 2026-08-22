"use client";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductImage } from "@/components/product-image";
import { SentimentBadge } from "@/components/sentiment-badge";
import { Sparkline } from "@/components/sparkline";
import { formatCompact, formatINR, timeAgo } from "@/lib/format";
import type { Product } from "@/lib/types";

interface Props {
  products: Product[];
  loading: boolean;
  total: number;
  onSelect: (product: Product) => void;
}

export function ProductTable({ products, loading, total, onSelect }: Props) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 rounded-xl border p-3">
            <Skeleton className="h-11 w-11 rounded-lg" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-1/3" />
            </div>
            <Skeleton className="h-6 w-20" />
          </div>
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 rounded-xl border border-dashed">
        <p className="text-sm text-muted-foreground">No products match these filters.</p>
        <p className="text-xs text-muted-foreground">Try widening the price range or clearing filters.</p>
      </div>
    );
  }

  return (
    <div>
      <p className="mb-2 text-xs text-muted-foreground">
        Showing {products.length} of {total} products · click a row for full detail
      </p>
      <div className="overflow-hidden rounded-xl border">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Product</th>
              <th className="hidden px-3 py-3 text-right font-medium md:table-cell">Price</th>
              <th className="hidden px-3 py-3 text-center font-medium md:table-cell">7d</th>
              <th className="hidden px-3 py-3 text-center font-medium lg:table-cell">Rating</th>
              <th className="px-3 py-3 text-center font-medium">Sentiment</th>
              <th className="hidden px-3 py-3 text-right font-medium sm:table-cell">Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {products.map((p) => (
              <tr
                key={p.id}
                onClick={() => onSelect(p)}
                className="cursor-pointer transition-colors hover:bg-muted/40"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <ProductImage name={p.name} brand={p.brand} imageUrl={p.image_url} size={40} />
                    <div className="min-w-0">
                      <p className="line-clamp-1 font-medium">{p.name}</p>
                      <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                        <span>{p.brand}</span>
                        <span>·</span>
                        <span>{p.category}</span>
                        {p.data_source && p.data_source !== "seed" && (
                          <Badge
                            variant={p.data_source === "live" ? "green" : "gray"}
                            className="px-1.5 text-[10px]"
                          >
                            {p.data_source}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="hidden px-3 py-3 text-right md:table-cell">
                  <p className="font-semibold tabular-nums">{formatINR(p.current_price)}</p>
                  <p className="text-xs text-muted-foreground">
                    <span className="line-through">{formatINR(p.mrp)}</span>
                    <span className="ml-1 text-brand">{p.discount_pct.toFixed(0)}% off</span>
                  </p>
                </td>
                <td className="hidden px-3 py-3 text-center md:table-cell">
                  <div className="inline-flex flex-col items-center gap-0.5">
                    <Sparkline data={p.price_trend} />
                    {p.price_change_24h !== 0 && (
                      <span
                        className={`text-[11px] font-medium ${
                          p.price_change_24h < 0 ? "text-red-500" : "text-brand"
                        }`}
                      >
                        {p.price_change_24h < 0 ? "▼" : "▲"} {Math.abs(p.price_change_24h).toFixed(1)}%
                      </span>
                    )}
                  </div>
                </td>
                <td className="hidden px-3 py-3 text-center lg:table-cell">
                  <p className="font-semibold">{p.rating.toFixed(1)}</p>
                  <p className="text-xs text-muted-foreground">{formatCompact(p.rating_count)} ratings</p>
                </td>
                <td className="px-3 py-3 text-center">
                  <SentimentBadge label={p.sentiment_label ?? "neutral"} />
                </td>
                <td className="hidden px-3 py-3 text-right text-xs text-muted-foreground sm:table-cell">
                  {timeAgo(p.last_updated)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
