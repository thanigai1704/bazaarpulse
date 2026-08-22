"use client";

import { useEffect, useState } from "react";
import { Bot, Truck, Store, PackageCheck } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SentimentBadge } from "@/components/sentiment-badge";
import { Stars } from "@/components/stars";
import { ProductImage } from "@/components/product-image";
import { PriceHistoryChart } from "@/components/charts/price-history-chart";
import { SentimentDonut, DonutLegend } from "@/components/charts/sentiment-donut";
import { WordCloud } from "@/components/charts/word-cloud";
import { api } from "@/lib/api";
import { formatCompact, formatINR, timeAgo } from "@/lib/format";
import type { Product, ProductDetail, ProductInsight, ReviewItem, SentimentLabel } from "@/lib/types";

interface Props {
  product: Product;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProductDetailModal({ product, open, onOpenChange }: Props) {
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [insight, setInsight] = useState<ProductInsight | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setDetail(null);
    setInsight(null);
    Promise.all([api.product(product.id), api.productInsight(product.id).catch(() => null)])
      .then(([d, i]) => {
        setDetail(d);
        setInsight(i);
      })
      .finally(() => setLoading(false));
  }, [open, product.id]);

  const reviews = detail?.reviews ?? [];
  const sentiment = detail?.sentiment ?? { positive: 0, negative: 0, neutral: 0 };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-start gap-3 pr-8">
            <ProductImage name={product.name} brand={product.brand} imageUrl={product.image_url} size={52} />
            <div>
              <p className="text-sm text-muted-foreground">{product.brand} · {product.category}</p>
              <h2 className="text-lg font-semibold leading-snug">{product.name}</h2>
            </div>
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Price + meta row */}
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-3xl font-bold text-foreground">{formatINR(detail?.current_price ?? product.current_price)}</p>
                <p className="text-sm text-muted-foreground">
                  MRP <span className="line-through">{formatINR(product.mrp)}</span>
                  <span className="ml-2 font-semibold text-brand">{product.discount_pct.toFixed(0)}% off</span>
                </p>
              </div>
              <div className="flex flex-col items-end gap-1 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5"><Store className="h-3.5 w-3.5" /> {product.seller}</span>
                <span className="flex items-center gap-1.5"><Truck className="h-3.5 w-3.5" /> {product.delivery_estimate}</span>
                <span className="flex items-center gap-1.5 text-brand">
                  <PackageCheck className="h-3.5 w-3.5" /> {product.stock_status}
                </span>
              </div>
            </div>

            {/* Price history */}
            <div>
              <h3 className="mb-2 text-sm font-semibold">Price History · 30 days</h3>
              <div className="rounded-xl border p-4">
                <PriceHistoryChart history={detail?.price_history ?? []} />
              </div>
            </div>

            {/* Sentiment + keywords + AI insight */}
            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-xl border p-4">
                <h3 className="mb-3 text-sm font-semibold">Sentiment Breakdown</h3>
                <div className="flex items-center gap-5">
                  <SentimentDonut
                    positive={sentiment.positive}
                    negative={sentiment.negative}
                    neutral={sentiment.neutral}
                    size={150}
                  />
                  <DonutLegend positive={sentiment.positive} negative={sentiment.negative} neutral={sentiment.neutral} />
                </div>
              </div>
              <div className="rounded-xl border p-4">
                <h3 className="mb-3 text-sm font-semibold">Top Review Keywords</h3>
                <WordCloud keywords={insight?.keywords ?? []} />
                <h3 className="mb-2 mt-5 text-sm font-semibold">Rating</h3>
                <div className="flex items-center gap-2">
                  <Stars rating={product.rating} />
                  <span className="text-sm font-semibold">{product.rating.toFixed(1)}</span>
                  <span className="text-xs text-muted-foreground">
                    ({formatCompact(product.rating_count)} ratings)
                  </span>
                </div>
              </div>
            </div>

            {/* AI insight box */}
            {insight?.ai_summary && (
              <div className="rounded-xl border-2 border-brand/50 bg-brand-light/60 p-4 dark:bg-brand/10">
                <p className="flex items-center gap-2 text-sm font-semibold text-brand-dark dark:text-brand">
                  <Bot className="h-4 w-4" /> AI Insight
                </p>
                <p className="mt-1 text-sm leading-relaxed">{insight.ai_summary}</p>
              </div>
            )}

            {/* Sample reviews */}
            <div>
              <h3 className="mb-2 text-sm font-semibold">Recent Reviews</h3>
              <div className="space-y-3">
                {reviews.slice(0, 4).map((review) => (
                  <ReviewCard key={review.id} review={review} />
                ))}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ReviewCard({ review }: { review: ReviewItem }) {
  return (
    <div className="rounded-xl border p-3">
      <div className="flex items-center justify-between gap-2">
        <Stars rating={review.star_rating} />
        <SentimentBadge label={review.sentiment_label as SentimentLabel} />
      </div>
      <p className="mt-2 text-sm leading-relaxed text-foreground/90">{review.review_text}</p>
      <p className="mt-1.5 text-xs text-muted-foreground">
        {timeAgo(review.scraped_at)}
        {review.is_synthetic && (
          <Badge variant="gray" className="ml-2 text-[10px]">synthetic</Badge>
        )}
      </p>
    </div>
  );
}
