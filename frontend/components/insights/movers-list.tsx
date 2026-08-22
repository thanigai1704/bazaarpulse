"use client";

import { TrendingDown, TrendingUp } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductImage } from "@/components/product-image";
import { formatINR, formatPercent } from "@/lib/format";
import type { MoverItem } from "@/lib/types";

interface Props {
  drops: MoverItem[];
  rises: MoverItem[];
  loading: boolean;
}

export function MoversList({ drops, rises, loading }: Props) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <TrendingDown className="h-4 w-4 text-brand" /> Biggest Price Drops · 24h
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MoverRows items={drops} loading={loading} drop />
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <TrendingUp className="h-4 w-4 text-red-500" /> Biggest Price Rises · 24h
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <MoverRows items={rises} loading={loading} />
        </CardContent>
      </Card>
    </div>
  );
}

function MoverRows({ items, loading, drop }: { items: MoverItem[]; loading: boolean; drop?: boolean }) {
  if (loading) {
    return (
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
    );
  }

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No price moves recorded yet this window.</p>;
  }

  return (
    <ul className="space-y-3">
      {items.map((m) => (
        <li key={m.product_id} className="flex items-center gap-3">
          <ProductImage name={m.name} brand={m.brand} imageUrl={m.image_url} size={40} />
          <div className="min-w-0 flex-1">
            <p className="line-clamp-1 text-sm font-medium">{m.name}</p>
            <p className="text-xs text-muted-foreground">
              {m.brand} · {m.category}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold tabular-nums">{formatINR(m.new_price)}</p>
            <p className={`text-xs font-semibold ${drop ? "text-brand" : "text-red-500"}`}>
              {formatPercent(m.change_pct)}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
