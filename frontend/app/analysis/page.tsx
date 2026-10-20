"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, BarChart3, Database, Info, Layers, Target } from "lucide-react";

import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { formatCompact, formatINR } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { MarketAnalysis } from "@/lib/types";

const CHART_TOOLTIP = {
  borderRadius: 10,
  border: "1px solid var(--border)",
  background: "var(--card)",
  fontSize: 12,
};

export default function AnalysisPage() {
  const { data, loading } = useApi<MarketAnalysis>(() => api.analysis(), []);

  if (loading || !data) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 lg:px-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      </div>
    );
  }

  const { overview: ov, data_quality: dq, price_dispersion: disp, discount_depth: disc, brand_concentration: bc, correlations: corr, outliers: out } = data;

  const dispersionChart = [...disp]
    .sort((a, b) => b.listings - a.listings)
    .slice(0, 14)
    .map((r) => ({
      category: r.category,
      median: r.median,
      mean: r.mean,
      q25: r.q25,
      q75: r.q75,
    }));

  const discountChart = [...disc]
    .sort((a, b) => b.mean_discount_pct - a.mean_discount_pct)
    .slice(0, 14)
    .map((r) => ({
      category: r.category,
      mean: r.mean_discount_pct,
      median: r.median_discount_pct,
      share: r.share_discounted_pct,
    }));

  const brandChart = bc.top_brands.slice(0, 10).map((b) => ({
    brand: b.brand.length > 14 ? `${b.brand.slice(0, 13)}…` : b.brand,
    listings: b.listings,
  }));

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 lg:px-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <BarChart3 className="h-6 w-6 text-brand" /> Market Analysis
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Descriptive statistics over {formatCompact(ov.listings)} real Flipkart listings
            (dataset snapshot). Every number below is computed from the loaded data — no
            synthetic values.
          </p>
        </div>
        <Badge variant="gray" className="text-xs">
          <Database className="mr-1 h-3 w-3" /> data_source: flipkart_2018
        </Badge>
      </div>

      {/* KPI strip */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Listings analysed" value={formatCompact(ov.listings)} sub={`${ov.categories} categories · ${formatCompact(ov.brands)} brands`} />
        <Kpi
          label="Price: median vs mean"
          value={formatINR(ov.price_median)}
          sub={`mean ${formatINR(ov.price_mean)} — mean is ${((ov.price_mean / ov.price_median)).toFixed(1)}× median (skewed)`}
        />
        <Kpi label="Discounts" value={`${ov.mean_discount_pct.toFixed(1)}% avg`} sub={`median ${ov.median_discount_pct.toFixed(1)}% · ${dq.discounted_share_pct}% of listings discounted`} />
        <Kpi
          label="Rating coverage"
          value={`${dq.rating_coverage_pct.toFixed(1)}%`}
          sub={`${formatCompact(dq.rated_listings)} of ${formatCompact(ov.listings)} listings rated`}
          warn={dq.rating_coverage_pct < 50}
        />
      </div>

      {/* Data quality callout */}
      <Card className={dq.rating_coverage_pct < 50 ? "border-amber-500/40" : ""}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <Database className="h-4 w-4" /> Data quality & selection bias
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <QualityStat
            label="Rating coverage"
            value={`${dq.rating_coverage_pct.toFixed(1)}%`}
            detail="Star ratings only exist for ~1 in 10 listings — any rating-based finding is drawn from this subsample."
          />
          <QualityStat
            label="Brand present"
            value={`${dq.brand_coverage_pct.toFixed(1)}%`}
            detail="Remaining rows tagged Unknown; brand-level stats cover the branded subset."
          />
          <QualityStat
            label="Mean price · rated vs unrated"
            value={
              dq.rated_vs_unrated.rated_mean_price != null && dq.rated_vs_unrated.unrated_mean_price != null
                ? `${formatINR(dq.rated_vs_unrated.rated_mean_price)} vs ${formatINR(dq.rated_vs_unrated.unrated_mean_price)}`
                : "—"
            }
            detail="Rated listings are cheaper on average — reviews skew toward low-ticket items (selection bias)."
          />
          <QualityStat
            label="Mean discount · rated vs unrated"
            value={
              dq.rated_vs_unrated.rated_mean_discount_pct != null && dq.rated_vs_unrated.unrated_mean_discount_pct != null
                ? `${dq.rated_vs_unrated.rated_mean_discount_pct.toFixed(1)}% vs ${dq.rated_vs_unrated.unrated_mean_discount_pct.toFixed(1)}%`
                : "—"
            }
            detail="Unrated listings carry deeper average discounts in this snapshot."
          />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Price dispersion */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <Layers className="h-4 w-4" /> Price dispersion by category
            </CardTitle>
            <CardDescription>
              Median (bar) vs mean (dot) per category. A large mean–median gap means the
              distribution is right-skewed and the mean is a poor summary.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={dispersionChart} margin={{ top: 8, right: 8, bottom: 40, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="category" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} angle={-35} textAnchor="end" height={56} interval={0} />
                  <YAxis tickFormatter={(v) => formatCompact(Number(v))} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={64} />
                  <Tooltip formatter={(v: number | string) => formatINR(Number(v))} contentStyle={CHART_TOOLTIP} cursor={{ fill: "var(--muted)", opacity: 0.3 }} />
                  <Bar dataKey="median" fill="#00A651" radius={[4, 4, 0, 0]} maxBarSize={26} />
                  <Line dataKey="mean" stroke="#F59E0B" strokeWidth={2} dot={{ r: 3, fill: "#F59E0B" }} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-1 pr-3 font-medium">Category</th>
                    <th className="py-1 pr-3 text-right font-medium">n</th>
                    <th className="py-1 pr-3 text-right font-medium">Q1</th>
                    <th className="py-1 pr-3 text-right font-medium">Median</th>
                    <th className="py-1 pr-3 text-right font-medium">Q3</th>
                    <th className="py-1 pr-3 text-right font-medium">Mean</th>
                    <th className="py-1 pr-3 text-right font-medium">CV</th>
                    <th className="py-1 text-right font-medium">Skew</th>
                  </tr>
                </thead>
                <tbody>
                  {disp.slice(0, 8).map((r) => (
                    <tr key={r.category} className="border-b last:border-0">
                      <td className="py-1.5 pr-3">{r.category}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{formatCompact(r.listings)}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{formatINR(r.q25)}</td>
                      <td className="py-1.5 pr-3 text-right font-medium tabular-nums">{formatINR(r.median)}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{formatINR(r.q75)}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{formatINR(r.mean)}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{r.cv?.toFixed(2)}</td>
                      <td className={`py-1.5 text-right tabular-nums ${r.skewness > 2 ? "text-red-500" : ""}`}>{r.skewness?.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Discount depth */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <Target className="h-4 w-4" /> Discount depth by category
            </CardTitle>
            <CardDescription>
              Mean (bar) vs median (line) discount %. Where the mean exceeds the median,
              a few extreme &quot;90% off&quot; anchors pull the average up.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={discountChart} margin={{ top: 8, right: 8, bottom: 40, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="category" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} angle={-35} textAnchor="end" height={56} interval={0} />
                  <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={44} />
                  <Tooltip formatter={(v: number | string) => `${Number(v).toFixed(1)}%`} contentStyle={CHART_TOOLTIP} cursor={{ fill: "var(--muted)", opacity: 0.3 }} />
                  <Bar dataKey="mean" fill="#6366F1" radius={[4, 4, 0, 0]} maxBarSize={26} />
                  <Line dataKey="median" stroke="#F59E0B" strokeWidth={2} dot={{ r: 3, fill: "#F59E0B" }} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-1 pr-3 font-medium">Category</th>
                    <th className="py-1 pr-3 text-right font-medium">Mean %</th>
                    <th className="py-1 pr-3 text-right font-medium">Median %</th>
                    <th className="py-1 pr-3 text-right font-medium">P90 %</th>
                    <th className="py-1 pr-3 text-right font-medium">Gap</th>
                    <th className="py-1 text-right font-medium">Share disc.</th>
                  </tr>
                </thead>
                <tbody>
                  {disc.slice(0, 8).map((r) => (
                    <tr key={r.category} className="border-b last:border-0">
                      <td className="py-1.5 pr-3">{r.category}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{r.mean_discount_pct.toFixed(1)}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{r.median_discount_pct.toFixed(1)}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{r.p90_discount_pct.toFixed(1)}</td>
                      <td className={`py-1.5 pr-3 text-right tabular-nums ${r.mean_vs_median_gap > 10 ? "text-amber-500" : ""}`}>{r.mean_vs_median_gap.toFixed(1)}</td>
                      <td className="py-1.5 text-right tabular-nums">{r.share_discounted_pct.toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Brand concentration */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <Layers className="h-4 w-4" /> Brand concentration
            </CardTitle>
            <CardDescription>
              Herfindahl-Hirschman Index on listing share: {bc.hhi.toFixed(4)} —{" "}
              <span className={bc.hhi >= 0.25 ? "text-red-500" : "text-brand"}>{bc.interpretation}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <Metric label="HHI" value={bc.hhi.toFixed(4)} />
              <Metric label="Top-5 share" value={`${bc.top5_share_pct.toFixed(1)}%`} />
              <Metric label="Top-10 share" value={`${bc.top10_share_pct.toFixed(1)}%`} />
              <Metric label="Pareto brands" value={`${bc.pareto_brand_count} (${bc.pareto_brand_pct.toFixed(0)}%)`} sub="cover 80% of listings" />
            </div>
            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={brandChart} layout="vertical" margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} />
                  <YAxis type="category" dataKey="brand" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={104} />
                  <Tooltip formatter={(v: number | string) => [formatCompact(Number(v)), "Listings"]} contentStyle={CHART_TOOLTIP} cursor={{ fill: "var(--muted)", opacity: 0.3 }} />
                  <Bar dataKey="listings" radius={[0, 4, 4, 0]} maxBarSize={16}>
                    {brandChart.map((_, i) => (
                      <Cell key={i} fill={i < 3 ? "#00A651" : "#94A3B8"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-muted-foreground">
              {bc.pareto_brand_count.toLocaleString()} brands ({bc.pareto_brand_pct.toFixed(0)}% of all
              brands in the catalogue) account for 80% of listings — a classic long tail.
            </p>
          </CardContent>
        </Card>

        {/* Correlations */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              <Info className="h-4 w-4" /> Correlations (Pearson r)
            </CardTitle>
            <CardDescription>
              Effect-size estimates, not significance tests. Small |r| is itself the finding.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <CorrRow
              label="Discount % vs star rating"
              r={corr.discount_vs_rating_r}
              n={corr.discount_vs_rating_n}
              note="Deep discounts do not buy better reviews in this snapshot."
            />
            <CorrRow label="Price vs discount %" r={corr.price_vs_discount_r} note={corr.price_vs_discount_note} />
            <CorrRow label="log(price) vs rating" r={corr.log_price_vs_rating_r} note="Log transform guards against the price outliers flagged below." />
            <p className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">{corr.discount_vs_rating_note}</p>
          </CardContent>
        </Card>
      </div>

      {/* Outliers */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <AlertTriangle className="h-4 w-4 text-amber-500" /> Price outliers
          </CardTitle>
          <CardDescription>
            Rule: {out.rule} — {out.outlier_count.toLocaleString()} listings flagged (
            {out.outlier_share_pct.toFixed(1)}% of the catalogue).
            {out.outlier_median_price != null && ` Their median price is ${formatINR(out.outlier_median_price)}.`}
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-1.5 pr-3 font-medium">Product</th>
                <th className="py-1.5 pr-3 font-medium">Category</th>
                <th className="py-1.5 pr-3 text-right font-medium">Price</th>
                <th className="py-1.5 pr-3 text-right font-medium">Cat. median</th>
                <th className="py-1.5 text-right font-medium">× median</th>
              </tr>
            </thead>
            <tbody>
              {out.top_outliers.map((o) => (
                <tr key={o.id} className="border-b last:border-0">
                  <td className="max-w-[320px] truncate py-2 pr-3">{o.name}</td>
                  <td className="py-2 pr-3">{o.category}</td>
                  <td className="py-2 pr-3 text-right font-medium tabular-nums">{formatINR(o.price)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{formatINR(o.category_median)}</td>
                  <td className="py-2 text-right tabular-nums text-amber-500">{o.vs_median_x.toFixed(1)}×</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

function Kpi({ label, value, sub, warn }: { label: string; value: string; sub?: string; warn?: boolean }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className={`mt-1 text-xl font-semibold tabular-nums ${warn ? "text-amber-500" : ""}`}>{value}</p>
        {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg bg-muted/40 p-3">
      <p className="text-[11px] font-medium text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-base font-semibold tabular-nums">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
    </div>
  );
}

function QualityStat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div>
      <p className="text-[11px] font-medium text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-base font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{detail}</p>
    </div>
  );
}

function CorrRow({ label, r, n, note }: { label: string; r: number | null; n?: number; note?: string }) {
  const strength =
    r == null ? "n/a" : Math.abs(r) < 0.1 ? "negligible" : Math.abs(r) < 0.3 ? "weak" : Math.abs(r) < 0.5 ? "moderate" : "strong";
  return (
    <div className="flex items-start justify-between gap-4 border-b pb-3 last:border-0">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {note && <p className="mt-0.5 text-xs text-muted-foreground">{note}</p>}
        {n != null && <p className="text-[11px] text-muted-foreground">n = {n.toLocaleString()} rated listings</p>}
      </div>
      <div className="text-right">
        <p className={`text-lg font-semibold tabular-nums ${r != null && Math.abs(r) < 0.1 ? "text-amber-500" : ""}`}>
          {r == null ? "—" : r.toFixed(3)}
        </p>
        <Badge variant="gray" className="mt-0.5 text-[10px]">{strength}</Badge>
      </div>
    </div>
  );
}
