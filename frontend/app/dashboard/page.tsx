"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { FiltersPanel } from "@/components/dashboard/filters-panel";
import { ProductTable } from "@/components/dashboard/product-table";
import { MoversCard } from "@/components/dashboard/movers-card";
import { ProductDetailModal } from "@/components/dashboard/product-detail-modal";
import { useProducts, type ProductFilters } from "@/hooks/useProducts";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { formatTime } from "@/lib/format";
import type { KpiSnapshot, Product, TrendingInsights } from "@/lib/types";

const DEFAULT_FILTERS: ProductFilters = {};

export default function DashboardPage() {
  const [filters, setFilters] = useState<ProductFilters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<Product | null>(null);

  const { products, total, loading, connected, refresh } = useProducts(filters);
  const { data: kpis, loading: kpiLoading, refresh: refreshKpis } = useApi<KpiSnapshot>(
    () => api.kpis(),
    [],
    60000,
  );
  const { data: movers, loading: moversLoading } = useApi<TrendingInsights>(
    () => api.trending(24),
    [],
    120000,
  );

  const updateFilters = (patch: Partial<ProductFilters>) => setFilters((f) => ({ ...f, ...patch }));
  const resetFilters = () => setFilters({});
  const manualRefresh = () => {
    refresh();
    refreshKpis();
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Market Dashboard</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
            <span className={`live-dot ${connected ? "" : "opacity-40"}`} />
            {connected ? "Live" : "Offline"} · last sync {formatTime(kpis?.last_synced)}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={manualRefresh}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      {/* KPIs */}
      <KpiCards data={kpis} loading={kpiLoading} connected={connected} />

      {/* Main grid */}
      <div className="mt-6 grid gap-6 lg:grid-cols-12">
        {/* Filters */}
        <aside className="lg:col-span-3">
          <div className="lg:sticky lg:top-20">
            <FiltersPanel filters={filters} onChange={updateFilters} onReset={resetFilters} />
          </div>
        </aside>

        {/* Table */}
        <section className="lg:col-span-6">
          <ProductTable products={products} loading={loading} total={total} onSelect={setSelected} />
        </section>

        {/* Movers */}
        <aside className="lg:col-span-3">
          <div className="lg:sticky lg:top-20">
            <MoversCard data={movers} loading={moversLoading} />
          </div>
        </aside>
      </div>

      {/* Detail modal */}
      {selected && (
        <ProductDetailModal product={selected} open={true} onOpenChange={(open) => !open && setSelected(null)} />
      )}
    </div>
  );
}
