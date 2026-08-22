"use client";

import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { formatINR } from "@/lib/format";
import type { ProductFilters } from "@/hooks/useProducts";

const CATEGORIES = ["Smartphones", "Laptops", "Home Appliances"];
const BRANDS = ["Samsung", "Xiaomi", "OnePlus", "Realme", "iQOO", "HP", "Dell", "Lenovo", "ASUS", "LG", "Bosch", "Voltas"];
const SORTS = [
  { value: "rating", label: "Top Rated" },
  { value: "price_asc", label: "Price: Low → High" },
  { value: "price_desc", label: "Price: High → Low" },
  { value: "discount", label: "Biggest Discount" },
  { value: "updated", label: "Recently Updated" },
];

interface FiltersPanelProps {
  filters: ProductFilters;
  onChange: (patch: Partial<ProductFilters>) => void;
  onReset: () => void;
}

export function FiltersPanel({ filters, onChange, onReset }: FiltersPanelProps) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Filters</h3>
        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={onReset}>
          <RotateCcw className="h-3 w-3" /> Reset
        </Button>
      </div>

      {/* Category */}
      <div>
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">Category</p>
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => {
            const active = filters.category === cat;
            return (
              <button
                key={cat}
                onClick={() => onChange({ category: active ? undefined : cat })}
                className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                  active
                    ? "border-brand bg-brand text-white"
                    : "border-border bg-background text-muted-foreground hover:border-brand/40 hover:text-foreground"
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* Brand */}
      <div>
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">Brand</p>
        <Select value={filters.brand ?? "all"} onValueChange={(v) => onChange({ brand: v === "all" ? undefined : v })}>
          <SelectTrigger className="h-9 text-xs">
            <SelectValue placeholder="All brands" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All brands</SelectItem>
            {BRANDS.map((b) => (
              <SelectItem key={b} value={b}>
                {b}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Price range */}
      <div>
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">
          Price range{" "}
          <span className="text-foreground">
            {formatINR(filters.minPrice ?? 9000)} – {formatINR(filters.maxPrice ?? 130000)}
          </span>
        </p>
        <Slider
          min={9000}
          max={130000}
          step={1000}
          value={[filters.minPrice ?? 9000, filters.maxPrice ?? 130000]}
          onValueChange={(v) => onChange({ minPrice: v[0], maxPrice: v[1] })}
        />
      </div>

      {/* Sentiment */}
      <div>
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">Sentiment</p>
        <Select
          value={filters.sentiment ?? "all"}
          onValueChange={(v) => onChange({ sentiment: v === "all" ? undefined : (v as ProductFilters["sentiment"]) })}
        >
          <SelectTrigger className="h-9 text-xs">
            <SelectValue placeholder="All sentiment" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All sentiment</SelectItem>
            <SelectItem value="positive">Positive 😊</SelectItem>
            <SelectItem value="neutral">Neutral 😐</SelectItem>
            <SelectItem value="negative">Negative 😞</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Sort */}
      <div>
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">Sort by</p>
        <Select value={filters.sortBy ?? "rating"} onValueChange={(v) => onChange({ sortBy: v })}>
          <SelectTrigger className="h-9 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORTS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
