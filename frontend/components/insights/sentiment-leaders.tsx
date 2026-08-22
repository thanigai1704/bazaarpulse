"use client";

import { Trophy } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductImage } from "@/components/product-image";
import { SentimentEmoji } from "@/components/sentiment-badge";
import type { SentimentLeader } from "@/lib/types";

export function SentimentLeaders({ data, loading }: { data: SentimentLeader[] | null; loading: boolean }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <Trophy className="h-4 w-4 text-amber-500" /> Most Loved Products
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-3.5 w-3/4" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
                <Skeleton className="h-5 w-16" />
              </div>
            ))}
          </div>
        ) : data && data.length > 0 ? (
          <ol className="space-y-3">
            {data.map((l, i) => (
              <li key={l.product_id} className="flex items-center gap-3">
                <span className="w-5 text-center text-sm font-bold text-muted-foreground">
                  {i < 3 ? ["🥇", "🥈", "🥉"][i] : i + 1}
                </span>
                <ProductImage name={l.name} brand={l.brand} imageUrl={l.image_url} size={40} />
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-1 text-sm font-medium">{l.name}</p>
                  <p className="text-xs text-muted-foreground">{l.brand}</p>
                </div>
                <div className="text-right">
                  <p className="flex items-center gap-1 text-sm font-semibold">
                    <SentimentEmoji label={l.sentiment_label} /> {Math.round(l.positive_share)}%
                  </p>
                  <p className="text-[11px] text-muted-foreground capitalize">{l.sentiment_label}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted-foreground">Sentiment leaders populate after reviews are processed.</p>
        )}
      </CardContent>
    </Card>
  );
}
