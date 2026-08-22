"use client";

import { ArrowDown, ArrowUp, Boxes, RefreshCw } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { SentimentEmoji } from "@/components/sentiment-badge";
import { formatINR, formatPercent, timeAgo } from "@/lib/format";
import type { KpiSnapshot } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";

interface KpiCardsProps {
  data: KpiSnapshot | null;
  loading: boolean;
  connected: boolean;
}

export function KpiCards({ data, loading, connected }: KpiCardsProps) {
  if (loading || !data) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="pt-6">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="mt-3 h-8 w-36" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const label = data.avg_sentiment_label;
  const drop = data.biggest_drop_24h;
  const dropBad = (drop?.change_pct ?? 0) > 0;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* Products tracked */}
      <Card>
        <CardContent className="pt-6">
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Boxes className="h-3.5 w-3.5" /> Products Tracked
          </p>
          <p className="mt-2 text-3xl font-bold tabular-nums">{data.products_tracked}</p>
          <p className="mt-1 text-xs text-muted-foreground">across 3 categories</p>
        </CardContent>
      </Card>

      {/* Avg sentiment */}
      <Card>
        <CardContent className="pt-6">
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">Avg Market Sentiment</p>
          <p className="mt-2 flex items-center gap-2 text-3xl font-bold">
            <SentimentEmoji label={label} /> {(data.avg_sentiment_score * 100).toFixed(0)}%
          </p>
          <p className="mt-1 text-xs text-muted-foreground capitalize">{label} across reviews</p>
        </CardContent>
      </Card>

      {/* Biggest price drop today */}
      <Card>
        <CardContent className="pt-6">
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <ArrowDown className="h-3.5 w-3.5" /> Biggest Price Drop Today
          </p>
          {drop ? (
            <>
              <p className="mt-2 truncate text-lg font-semibold leading-tight">{drop.name}</p>
              <p className="mt-1 flex items-center gap-1.5 text-sm">
                <span className="font-bold text-brand">{formatINR(drop.new_price)}</span>
                <span className="inline-flex items-center gap-0.5 text-xs font-medium text-red-500">
                  <ArrowDown className="h-3 w-3" />
                  {formatPercent(drop.change_pct)}
                </span>
              </p>
            </>
          ) : (
            <p className="mt-2 text-lg font-semibold">—</p>
          )}
          <p className="mt-1 text-xs text-muted-foreground">{drop?.category ?? "no moves yet"}</p>
        </CardContent>
      </Card>

      {/* Last synced */}
      <Card>
        <CardContent className="pt-6">
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <RefreshCw className="h-3.5 w-3.5" /> Last Synced
          </p>
          <p className="mt-2 flex items-center gap-2 text-2xl font-bold">
            <span className={`live-dot ${connected ? "" : "opacity-40"}`} />
            {timeAgo(data.last_synced)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {connected ? "live feed connected" : "live feed offline"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

/** Small helper reused by insights page. */
export function ChangeChip({ value }: { value: number }) {
  const down = value <= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-xs font-semibold ${
        down ? "bg-brand-light text-brand-dark dark:bg-brand/15 dark:text-brand" : "bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400"
      }`}
    >
      {down ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />}
      {formatPercent(value)}
    </span>
  );
}
