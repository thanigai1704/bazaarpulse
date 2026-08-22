"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatINR, formatDate } from "@/lib/format";
import type { PricePoint } from "@/lib/types";

export function PriceHistoryChart({ history }: { history: PricePoint[] }) {
  const data = history.map((h) => ({
    date: formatDate(h.recorded_at),
    price: h.price,
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-muted-foreground">
        No price history yet — it builds as live cycles run.
      </div>
    );
  }

  const min = Math.min(...data.map((d) => d.price));
  const max = Math.max(...data.map((d) => d.price));
  const pad = Math.max(500, Math.round((max - min) * 0.15));

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} minTickGap={24} />
          <YAxis
            domain={[min - pad, max + pad]}
            tickFormatter={(v) => formatINR(v)}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            tickLine={false}
            axisLine={false}
            width={86}
          />
          <Tooltip
            formatter={(value: number | string) => [formatINR(Number(value)), "Price"]}
            contentStyle={{
              borderRadius: 10,
              border: "1px solid var(--border)",
              background: "var(--card)",
              fontSize: 12,
            }}
          />
          <Line type="monotone" dataKey="price" stroke="#00A651" strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
