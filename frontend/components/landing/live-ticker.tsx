"use client";

import { ArrowDown, ArrowUp } from "lucide-react";

import { useProducts } from "@/hooks/useProducts";
import { formatINR, formatPercent } from "@/lib/format";
import type { Product } from "@/lib/types";

function TickerItem({ product }: { product: Product }) {
  const drop = product.price_change_24h <= 0;
  return (
    <span className="mx-6 inline-flex items-center gap-2 whitespace-nowrap text-sm">
      <span className="max-w-[220px] truncate font-medium text-foreground">{product.name}</span>
      <span className="font-semibold text-foreground">{formatINR(product.current_price)}</span>
      <span
        className={`inline-flex items-center gap-0.5 text-xs font-medium ${
          drop ? "text-red-500" : "text-brand"
        }`}
      >
        {drop ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />}
        {formatPercent(product.price_change_24h)}
      </span>
    </span>
  );
}

/** NSE/BSE-style scrolling price ticker. Duplicated track for seamless loop. */
export function LiveTicker() {
  const { products, connected } = useProducts({ sortBy: "updated" });

  if (products.length === 0) {
    return (
      <div className="flex h-10 items-center border-b bg-brand-dark px-4 text-sm text-white">
        Loading live market feed…
      </div>
    );
  }

  const track = (
    <div className="flex items-center">
      {products.slice(0, 24).map((p) => (
        <TickerItem key={p.id} product={p} />
      ))}
    </div>
  );

  return (
    <div className="relative flex h-10 items-center overflow-hidden border-b bg-brand-dark text-white">
      <span className="absolute left-0 z-10 flex h-full items-center gap-1.5 bg-brand-dark px-3 text-xs font-semibold uppercase tracking-wider">
        <span className={`live-dot ${connected ? "" : "opacity-40"}`} />
        {connected ? "Live" : "Connecting"}
      </span>
      <div className="ticker-track pl-28">
        {track}
        {track}
      </div>
    </div>
  );
}
