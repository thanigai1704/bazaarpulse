"use client";

import { TrendingDown, TrendingUp } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatINR, formatPercent } from "@/lib/format";
import type { TrendingInsights } from "@/lib/types";

export function MoversCard({ data, loading }: { data: TrendingInsights | null; loading: boolean }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">Market Movers · 24h</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <MoverSection
          title="Top Price Drops"
          icon={<TrendingDown className="h-3.5 w-3.5 text-brand" />}
          rows={data?.biggest_drops ?? []}
          loading={loading}
        />
        <MoverSection
          title="Top Price Rises"
          icon={<TrendingUp className="h-3.5 w-3.5 text-red-500" />}
          rows={data?.biggest_rises ?? []}
          loading={loading}
        />
      </CardContent>
    </Card>
  );
}

function MoverSection({
  title,
  icon,
  rows,
  loading,
}: {
  title: string;
  icon: React.ReactNode;
  rows: { name: string; old_price: number; new_price: number; change_pct: number }[];
  loading: boolean;
}) {
  return (
    <div>
      <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        {icon} {title}
      </p>
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="text-xs text-muted-foreground">No price moves recorded yet.</p>
      ) : (
        <ul className="space-y-2">
          {rows.slice(0, 4).map((m) => (
            <li key={m.name} className="flex items-baseline justify-between gap-2 text-sm">
              <span className="line-clamp-1">{m.name}</span>
              <span className="whitespace-nowrap text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">{formatINR(m.new_price)}</span>{" "}
                <span className="text-brand">{formatPercent(m.change_pct)}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
