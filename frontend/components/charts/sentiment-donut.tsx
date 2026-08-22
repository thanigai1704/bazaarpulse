"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { cn } from "@/lib/utils";

const COLORS = { positive: "#00A651", negative: "#EF4444", neutral: "#9CA3AF" };

export function SentimentDonut({
  positive,
  negative,
  neutral,
  size = 180,
  className,
}: {
  positive: number;
  negative: number;
  neutral: number;
  size?: number;
  className?: string;
}) {
  const data = [
    { name: "Positive", value: positive, color: COLORS.positive },
    { name: "Negative", value: negative, color: COLORS.negative },
    { name: "Neutral", value: neutral, color: COLORS.neutral },
  ];

  return (
    <div className={cn("relative", className)} style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            innerRadius={size * 0.32}
            outerRadius={size * 0.46}
            paddingAngle={3}
            strokeWidth={0}
            isAnimationActive={false}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v: number | string, name: string) => [`${v}%`, name]}
            contentStyle={{
              borderRadius: 10,
              border: "1px solid var(--border)",
              background: "var(--card)",
              fontSize: 12,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold">{Math.round(positive)}%</span>
        <span className="text-xs text-muted-foreground">positive</span>
      </div>
    </div>
  );
}

export function DonutLegend({
  positive,
  negative,
  neutral,
}: {
  positive: number;
  negative: number;
  neutral: number;
}) {
  const items = [
    { label: "Positive", value: positive, color: COLORS.positive },
    { label: "Negative", value: negative, color: COLORS.negative },
    { label: "Neutral", value: neutral, color: COLORS.neutral },
  ];
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-2 text-sm">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: item.color }} />
          <span className="text-muted-foreground">{item.label}</span>
          <span className="ml-auto font-semibold tabular-nums">{item.value}%</span>
        </div>
      ))}
    </div>
  );
}
